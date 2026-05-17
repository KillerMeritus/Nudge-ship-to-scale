use std::process::Command;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WindowEvent,
};

use tauri_plugin_notification::NotificationExt;

// ── Health-check constants ────────────────────────────────────────────────────
/// URL polled until the FastAPI sidecar signals it is ready.
const HEALTH_URL: &str = "http://127.0.0.1:8080/health";

/// Interval between successive health-check attempts.
const POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Maximum time to wait for the backend before showing the window anyway.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(15);

// ── Shared timer state (Rust-side mirror of the JS timer) ────────────────────
// The JS side calls the `update_tray_timer` Tauri command every tick to push
// its state here. The tray menu reads it when rebuilding the label.

#[derive(Clone)]
struct TrayState {
    timer_label: String, // e.g. "Focus: 22:14 remaining" or "Idle"
    active_task: String,
    distraction_count: u32,
}

// ── Tauri command — called from JS Timer component every second ───────────────

/// Update the tray's timer label from JS.
///
/// The Timer component calls this command each tick so the tray always shows
/// live remaining time without Rust needing to own the countdown logic.
#[tauri::command]
fn update_tray_timer(
    app: AppHandle,
    state: tauri::State<Arc<Mutex<TrayState>>>,
    label: String,
) {
    let ts = {
        let mut s = state.lock().unwrap();
        s.timer_label = label.clone();
        s.clone()
    };

    // Rebuild the tray menu so the label item reflects the update.
    // We ignore errors here — tray menu rebuild is best-effort.
    let _ = rebuild_tray_menu(&app, &ts);
}

// ── Tray menu builder ─────────────────────────────────────────────────────────

/// Construct (or reconstruct) the tray context menu.
///
/// Called once at startup and again every time the timer label changes.
/// Returns the new menu so the caller can attach it to the tray icon.
fn rebuild_tray_menu(app: &AppHandle, state: &TrayState) -> tauri::Result<Menu<tauri::Wry>> {
    let menu = Menu::new(app)?;

    // Item 0 — Live timer status (read-only display label)
    let status_text = if state.timer_label.is_empty() {
        "Nudge — Idle".to_string()
    } else {
        state.timer_label.clone()
    };
    let status = MenuItem::with_id(app, "status", &status_text, false, None::<&str>)?;

    let task_text = format!("Task: {}", state.active_task);
    let task_item = MenuItem::with_id(app, "task", &task_text, false, None::<&str>)?;

    let dist_text = format!("Distractions today: {}", state.distraction_count);
    let dist_item = MenuItem::with_id(app, "distractions", &dist_text, false, None::<&str>)?;

    // Item 1 — Separator-equivalent: disabled dash item
    let sep = MenuItem::with_id(app, "sep", "─────────────", false, None::<&str>)?;

    // Item 2 — Open / show window
    let open = MenuItem::with_id(app, "open", "Open Nudge", true, None::<&str>)?;

    // Item 3 — Emit "start-focus" event that the JS Timer listens for
    let start_focus = MenuItem::with_id(app, "start_focus", "▶  Start Focus Session", true, None::<&str>)?;

    // Item 4 — Emit "pause-timer" event
    let pause = MenuItem::with_id(app, "pause", "⏸  Pause Timer", true, None::<&str>)?;

    // Item 5 — Hard quit
    let quit = MenuItem::with_id(app, "quit", "Quit Nudge", true, None::<&str>)?;

    menu.append(&status)?;
    menu.append(&task_item)?;
    menu.append(&dist_item)?;
    menu.append(&sep)?;
    menu.append(&open)?;
    menu.append(&start_focus)?;
    menu.append(&pause)?;
    menu.append(&quit)?;

    Ok(menu)
}

// ── Helper: show + focus the main window ─────────────────────────────────────

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn to_iso(t: std::time::SystemTime) -> String {
    let dt: chrono::DateTime<chrono::Utc> = t.into();
    dt.to_rfc3339()
}

// ── Entry point ───────────────────────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Step 1 — Spawn the FastAPI/uvicorn sidecar in a separate OS process.
    // The process is detached; Tauri does NOT own its lifecycle unless we kill it on quit.
    let backend_child = Arc::new(Mutex::new(
        Command::new("backend/.venv/bin/python3")
            .current_dir("..")
            .args([
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
            ])
            .spawn()
            .expect("failed to start backend sidecar")
    ));

    let backend_child_ref = backend_child.clone();

    // Step 2 — Shared timer state accessible to both the Tauri command and the
    //          tray menu builder. Arc<Mutex<>> lets us share across threads safely.
    let tray_state = Arc::new(Mutex::new(TrayState {
        timer_label: String::new(),
        active_task: "No active task".to_string(),
        distraction_count: 0,
    }));
    let tray_state_clone = tray_state.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--autostart"]),
        ))
        // Register the JS→Rust command
        .invoke_handler(tauri::generate_handler![update_tray_timer])
        // Make TrayState available via tauri::State<>
        .manage(tray_state)
        .setup(move |app| {
            let app_handle = app.handle().clone();

            // ── Step 3: Health-check thread ──────────────────────────────────
            // Poll /health every 500 ms; show window once backend is ready.
            {
                let handle = app_handle.clone();
                thread::spawn(move || {
                    let client = reqwest::blocking::Client::builder()
                        .timeout(Duration::from_secs(2))
                        .build()
                        .expect("failed to build HTTP client");

                    let deadline = Instant::now() + STARTUP_TIMEOUT;
                    let mut backend_ready = false;

                    while Instant::now() < deadline {
                        match client.get(HEALTH_URL).send() {
                            Ok(resp) if resp.status().is_success() => {
                                println!("[Nudge] Backend is ready — showing window.");
                                backend_ready = true;
                                break;
                            }
                            _ => thread::sleep(POLL_INTERVAL),
                        }
                    }

                    if !backend_ready {
                        println!(
                            "[Nudge] WARNING: backend did not respond within {}s.",
                            STARTUP_TIMEOUT.as_secs()
                        );
                    }

                    // Only show the window if we were launched manually.
                    let is_autostart = std::env::args().any(|arg| arg == "--autostart");
                    if !is_autostart {
                        show_main_window(&handle);
                    } else {
                        println!("[Nudge] Launched via autostart — keeping window hidden in tray.");
                    }
                });
            }

            // ── Step 4: System tray setup ────────────────────────────────────
            let ts = tray_state_clone.lock().unwrap().clone();
            let initial_menu = rebuild_tray_menu(app.handle(), &ts)
                .expect("failed to build tray menu");

            // Load the 32×32 icon from the bundled icons directory.
            // Image::from_path resolves relative to the resource dir at runtime.
            let icon = app.default_window_icon()
                .expect("no default window icon — check tauri.conf.json")
                .clone();

            // Build the tray icon. On macOS this appears in the menu bar.
            let _tray = TrayIconBuilder::new()
                .icon(icon)
                .menu(&initial_menu)
                .show_menu_on_left_click(false) // left-click → show window
                .tooltip("Nudge — Productivity Timer")
                .on_tray_icon_event({
                    // Left-click on tray icon → restore + focus main window.
                    let handle = app_handle.clone();
                    move |_tray, event| {
                        if let TrayIconEvent::Click {
                            button: MouseButton::Left,
                            button_state: MouseButtonState::Up,
                            ..
                        } = event
                        {
                            show_main_window(&handle);
                        }
                    }
                })
                .on_menu_event({
                    // Handle the four tray menu actions.
                    let handle = app_handle.clone();
                    move |app, event| match event.id.as_ref() {
                        "open" => {
                            // Restore the main window.
                            show_main_window(&handle);
                        }
                        "start_focus" => {
                            // Emit an event to the JS frontend — Timer listens for this.
                            show_main_window(&handle);
                            let _ = app.emit("tray-start-focus", ());
                        }
                        "pause" => {
                            // Emit pause event to JS Timer.
                            let _ = app.emit("tray-pause-timer", ());
                        }
                        "quit" => {
                            // Hard exit — this is intentional quit from tray.
                            if let Ok(mut child) = backend_child_ref.lock() {
                                let _ = child.kill();
                                println!("[Nudge] Backend sidecar killed.");
                            }
                            println!("[Nudge] Quit requested from tray menu.");
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .build(app)?;

            // ── Step 5: Window close → hide (not quit) ───────────────────────
            // Intercept the CloseRequested event on "main" so that clicking ✕
            // hides the window instead of terminating the process. The app
            // continues to run in the tray until the user chooses "Quit Nudge".
            if let Some(window) = app.get_webview_window("main") {
                let app_handle_close = app_handle.clone();
                window.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        // Prevent the default close/quit behaviour.
                        api.prevent_close();
                        // Hide the window — app lives on in tray.
                        if let Some(w) = app_handle_close.get_webview_window("main") {
                            let _ = w.hide();
                            println!("[Nudge] Window hidden — app running in tray.");
                        }
                    }
                });
            }

            // ── Step 6: Sleep/Wake detection thread ──────────────────────────────────
            {
                let handle = app_handle.clone();
                thread::spawn(move || {
                    use std::time::SystemTime;

                    let client = reqwest::blocking::Client::builder()
                        .timeout(Duration::from_secs(5))
                        .build()
                        .expect("http client");

                    const POLL: Duration = Duration::from_secs(5);
                    const SLEEP_THRESHOLD: Duration = Duration::from_secs(30);

                    let mut last_tick = SystemTime::now();
                    let mut asleep = false;
                    let mut slept_at: Option<SystemTime> = None;

                    loop {
                        thread::sleep(POLL);
                        let now = SystemTime::now();
                        let gap = now.duration_since(last_tick).unwrap_or_default();

                        if gap > SLEEP_THRESHOLD && !asleep {
                            // Machine was sleeping
                            asleep = true;
                            slept_at = Some(last_tick);
                            println!("[Nudge] System sleep detected — gap: {}s", gap.as_secs());

                            // Emit to React
                            let _ = handle.emit("system-sleep", ());

                            // Signal scraper to pause
                            let _ = client
                                .post("http://127.0.0.1:8080/scraper/pause")
                                .send();

                        } else if gap <= SLEEP_THRESHOLD && asleep {
                            // Woke up
                            asleep = false;
                            let woke_at = now;
                            let slept_at_ts = slept_at.unwrap_or(now);

                            let slept_at_iso = to_iso(slept_at_ts);
                            let woke_at_iso = to_iso(woke_at);
                            let duration_secs = gap.as_secs() as i64;

                            println!("[Nudge] System wake detected — slept for {}s", duration_secs);

                            // Emit to React
                            let _ = handle.emit("system-wake", serde_json::json!({
                                "slept_at": slept_at_iso,
                                "woke_at": woke_at_iso,
                                "duration_seconds": duration_secs,
                            }));

                            // Signal scraper to resume
                            let _ = client
                                .post("http://127.0.0.1:8080/scraper/resume")
                                .send();

                            // Log sleep gap to BE-1 activity log
                            let body = serde_json::json!({
                                "slept_at": slept_at_iso,
                                "woke_at": woke_at_iso,
                                "duration_seconds": duration_secs,
                            });
                            let _ = client
                                .post("http://127.0.0.1:8080/activity/sleep-gap")
                                .json(&body)
                                .send();

                            // Health check backend
                            if client.get("http://127.0.0.1:8080/health").send().is_err() {
                                println!("[Nudge] WARNING: Backend not responding after wake — may need restart.");
                                let _ = handle.emit("backend-offline", ());
                            }
                        }

                        last_tick = now;
                    }
                });
            }

            // ── Step 7: Tray active-task + distraction poll ──────────────────────────
            {
                let handle = app_handle.clone();
                let tray_ref = tray_state_clone.clone();

                thread::spawn(move || {
                    let client = reqwest::blocking::Client::builder()
                        .timeout(Duration::from_secs(5))
                        .build()
                        .expect("http client");

                    // Keep track of distractions we've already notified about
                    let mut known_distraction_count: u32 = 0;

                    loop {
                        thread::sleep(Duration::from_secs(10));

                        // Poll active task
                        let active_task_label = client
                            .get("http://127.0.0.1:8080/timer/active-task")
                            .send()
                            .ok()
                            .and_then(|r| r.json::<serde_json::Value>().ok())
                            .and_then(|v| v["title"].as_str().map(|s| s.to_string()))
                            .unwrap_or_else(|| "No active task".to_string());

                        // Poll distractions
                        let dist_response = client
                            .get("http://127.0.0.1:8080/distraction/today")
                            .send()
                            .ok()
                            .and_then(|r| r.json::<serde_json::Value>().ok());

                        let mut dist_count = 0;
                        if let Some(v) = &dist_response {
                            if let Some(arr) = v.as_array() {
                                dist_count = arr.len() as u32;

                                // Fire notification for new distractions
                                if dist_count > known_distraction_count {
                                    for i in known_distraction_count..dist_count {
                                        if let Some(event) = arr.get(i as usize) {
                                            let task_title = event["task_title"].as_str().unwrap_or("Unknown Task");
                                            let app_name = event["app_name"].as_str().unwrap_or("Unknown App");
                                            let reason = event["reason"].as_str().unwrap_or("You seem distracted.");

                                            let body = format!("You switched to {} while working on \"{}\" — {}", app_name, task_title, reason);
                                            let _ = handle.notification()
                                                .builder()
                                                .title("Hey, you seem distracted 👀")
                                                .body(&body)
                                                .show();
                                            println!("[Nudge] Distraction notification shown: {}", body);
                                        }
                                    }
                                    known_distraction_count = dist_count;
                                } else if dist_count < known_distraction_count {
                                    // Day reset or cleared
                                    known_distraction_count = dist_count;
                                }
                            }
                        }

                        // Update shared tray state
                        {
                            let mut ts = tray_ref.lock().unwrap();
                            ts.active_task = active_task_label;
                            ts.distraction_count = dist_count;
                        }

                        // Rebuild tray
                        let ts = tray_ref.lock().unwrap().clone();
                        let _ = rebuild_tray_menu(&handle, &ts);
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}