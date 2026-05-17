import { useState, useEffect } from 'react';
import { useActiveTask } from '../../contexts/ActiveTaskContext';

const formatEstimate = (h, m) => {
  const hours = parseInt(h) || 0;
  const mins = parseInt(m) || 0;
  if (hours === 0 && mins === 0) return null;
  if (hours === 0) return `${mins}m`;
  return `${hours}h ${mins.toString().padStart(2, '0')}m`;
};

const fmt = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  if (h > 0) return `${h}:${m}:${s}`;
  return `${m}:${s}`;
};

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newHours, setNewHours] = useState('');
  const [newMinutes, setNewMinutes] = useState('');

  // Inline edit state
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editHours, setEditHours] = useState('');
  const [editMinutes, setEditMinutes] = useState('');

  // Inline delete confirm state
  const [deletingTaskId, setDeletingTaskId] = useState(null);

  const { activeTask, taskStatus, elapsedSeconds, startTask, pauseTask, resumeTask, clearTask } = useActiveTask();

  // Load tasks from backend on startup
  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch("http://localhost:8080/tasks");
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error("Failed to fetch tasks:", error);
    }
  };

  // Add task
  const addTask = async (e) => {
    e.preventDefault();

    if (!newTaskTitle.trim()) return;

    const h = parseInt(newHours) || 0;
    const m = parseInt(newMinutes) || 0;
    if (h < 0 || h > 23 || m < 0 || m > 59) return;

    try {
      const response = await fetch("http://localhost:8080/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: newTaskTitle.trim(),
          estimated_hours: h,
          estimated_minutes: m,
          tags: [],
        }),
      });

      const newTask = await response.json();

      setTasks([newTask, ...tasks]);
      setNewTaskTitle('');
      setNewHours('');
      setNewMinutes('');
    } catch (error) {
      console.error("Failed to add task:", error);
    }
  };

  // Toggle task complete/incomplete
  const toggleTask = async (id) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;

    if (activeTask && activeTask.id === id) {
      clearTask();
    }

    const updatedStatus = task.status === "Done" ? "Todo" : "Done";

    try {
      const response = await fetch(`http://localhost:8080/tasks/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: updatedStatus,
        }),
      });

      const updatedTask = await response.json();

      setTasks(tasks.map(t =>
        t.id === id ? updatedTask : t
      ));
    } catch (error) {
      console.error("Failed to update task:", error);
    }
  };

  const confirmDelete = (id) => setDeletingTaskId(id);
  const cancelDelete = () => setDeletingTaskId(null);

  // Delete task
  const deleteTask = async (id) => {
    try {
      await fetch(`http://localhost:8080/tasks/${id}`, {
        method: "DELETE",
      });

      setTasks(tasks.filter(t => t.id !== id));
      if (activeTask && activeTask.id === id) {
        clearTask();
      }
      setDeletingTaskId(null);
    } catch (error) {
      console.error("Failed to delete task:", error);
    }
  };

  const startEdit = (task) => {
    setEditingTaskId(task.id);
    setEditTitle(task.title);
    setEditHours(task.estimated_hours || '');
    setEditMinutes(task.estimated_minutes || '');
    setDeletingTaskId(null);
  };

  const cancelEdit = () => {
    setEditingTaskId(null);
  };

  const saveEdit = async (id) => {
    const h = parseInt(editHours) || 0;
    const m = parseInt(editMinutes) || 0;
    if (h < 0 || h > 23 || m < 0 || m > 59) return;

    try {
      const response = await fetch(`http://localhost:8080/tasks/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle.trim(),
          estimated_hours: h,
          estimated_minutes: m,
        }),
      });
      const updatedTask = await response.json();
      setTasks(tasks.map(t => t.id === id ? updatedTask : t));
      setEditingTaskId(null);
    } catch (error) {
      console.error("Failed to update task:", error);
    }
  };

  return (
    <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg flex flex-col gap-stack-md">
      
      {/* Headers */}
      <header className="flex flex-col gap-unit mb-stack-md">
        <h1 className="font-headline-xl text-headline-xl text-on-surface">Tasks</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant">Today's Focus</p>
      </header>

      {/* Add Task Input */}
      <form 
        onSubmit={addTask}
        className="bg-surface-container-low rounded-lg p-unit mb-stack-sm border border-transparent focus-within:border-outline-variant transition-colors flex flex-col sm:flex-row items-center gap-2 px-3 py-2"
      >
        <span className="material-symbols-outlined text-outline">add</span>
        <input 
          type="text" 
          placeholder="What needs to be done?" 
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          className="w-full bg-transparent border-none focus:ring-0 font-body-md text-body-md text-on-surface placeholder-outline-variant p-2 outline-none"
        />
        <div className="flex items-center gap-2 shrink-0">
          <input 
            type="number"
            min="0" max="23"
            placeholder="h"
            value={newHours}
            onChange={(e) => setNewHours(e.target.value)}
            className="w-14 bg-surface rounded px-2 py-1 border border-outline-variant focus:border-primary text-body-md"
          />
          <span className="text-on-surface-variant font-body-md">:</span>
          <input 
            type="number"
            min="0" max="59"
            placeholder="m"
            value={newMinutes}
            onChange={(e) => setNewMinutes(e.target.value)}
            className="w-14 bg-surface rounded px-2 py-1 border border-outline-variant focus:border-primary text-body-md"
          />
          <button 
            type="submit" 
            disabled={!newTaskTitle.trim()}
            className="ml-2 px-4 py-1.5 bg-primary text-on-primary font-label-md rounded hover:bg-surface-tint disabled:opacity-50 transition-colors"
          >
            Add
          </button>
        </div>
      </form>

      {/* Task List */}
      <div className="flex flex-col gap-0 border-t border-outline-variant">
        {tasks.length === 0 ? (
          <p className="text-on-surface-variant text-center mt-stack-md italic">No tasks yet. Enjoy your day! 🎉</p>
        ) : (
          [...tasks].sort((a, b) => {
            if (activeTask && a.id === activeTask.id) return -1;
            if (activeTask && b.id === activeTask.id) return 1;
            return 0;
          }).map(task => {
            const isDeleting = deletingTaskId === task.id;
            const isEditing = editingTaskId === task.id;
            const estStr = formatEstimate(task.estimated_hours, task.estimated_minutes);
            const isDone = task.status === "Done";
            const isRunningTask = activeTask?.id === task.id;
            const isRunning = isRunningTask && taskStatus === 'running';
            const isPaused = isRunningTask && taskStatus === 'paused';

            let displayTime = '';
            if (isRunningTask) {
              const totalSecs = (task.estimated_hours || 0) * 3600 + (task.estimated_minutes || 0) * 60;
              if (totalSecs > 0) {
                const remaining = totalSecs - elapsedSeconds;
                displayTime = remaining < 0 ? `-${fmt(Math.abs(remaining))}` : fmt(remaining);
              } else {
                displayTime = fmt(elapsedSeconds);
              }
            }

            if (isEditing) {
              return (
                <div key={task.id} className="flex flex-col gap-3 py-stack-sm border-b border-surface-variant px-2 -mx-2 rounded bg-surface-container-low">
                  <input 
                    type="text" 
                    className="w-full bg-surface border border-outline-variant rounded p-2 focus:border-primary font-body-md"
                    value={editTitle} 
                    onChange={(e) => setEditTitle(e.target.value)} 
                    autoFocus 
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-on-surface-variant font-label-sm">Est:</span>
                    <input 
                      type="number" min="0" max="23" placeholder="h" 
                      className="w-14 bg-surface rounded px-2 py-1 border border-outline-variant"
                      value={editHours} onChange={(e) => setEditHours(e.target.value)} 
                    />
                    <input 
                      type="number" min="0" max="59" placeholder="m" 
                      className="w-14 bg-surface rounded px-2 py-1 border border-outline-variant"
                      value={editMinutes} onChange={(e) => setEditMinutes(e.target.value)} 
                    />
                    <div className="flex-1"></div>
                    <button onClick={() => saveEdit(task.id)} className="px-3 py-1 bg-primary text-on-primary font-label-md rounded">Save</button>
                    <button onClick={cancelEdit} className="px-3 py-1 bg-surface-variant text-on-surface font-label-md rounded">Cancel</button>
                  </div>
                </div>
              );
            }

            return (
              <div 
                key={task.id} 
                className={`group flex items-center gap-4 py-stack-sm border-b border-surface-variant hover:bg-surface-container-low transition-colors px-2 -mx-2 rounded ${isRunningTask ? 'border-l-4 border-l-primary bg-surface-container-low/50' : ''}`}
              >
                <input 
                  type="checkbox" 
                  className="flex-shrink-0 cursor-pointer form-checkbox h-5 w-5 rounded border-outline text-primary focus:ring-primary bg-surface transition duration-150 ease-in-out" 
                  checked={isDone}
                  onChange={() => toggleTask(task.id)}
                />
                
                <div className="flex-1 min-w-0">
                  <h3 className={`font-body-md text-body-md truncate ${isDone ? 'text-on-surface-variant line-through' : 'text-on-surface'}`}>
                    {task.title}
                  </h3>
                  
                  {/* Progress Display for Running Tasks */}
                  {isRunningTask && (
                     <div className="font-label-sm text-label-sm text-primary mt-1">
                       Active: {displayTime} {estStr && ` / ${estStr}`}
                     </div>
                  )}
                </div>

                <div className={`flex items-center gap-4 flex-shrink-0 transition-opacity ${!isRunningTask && !isDeleting ? 'opacity-100 md:opacity-0 group-hover:opacity-100' : 'opacity-100'}`}>
                  {/* Estimate Pill */}
                  {!isRunningTask && estStr && (
                    <span className="font-label-sm text-label-sm text-on-surface-variant bg-surface-variant px-2 py-1 rounded-full">
                      {estStr}
                    </span>
                  )}

                  {/* Actions */}
                  {isDeleting ? (
                    <div className="flex items-center gap-2">
                      <span className="text-error font-label-sm">Delete?</span>
                      <button onClick={() => deleteTask(task.id)} className="text-error hover:underline font-label-sm">Yes</button>
                      <button onClick={cancelDelete} className="text-on-surface-variant hover:underline font-label-sm">No</button>
                    </div>
                  ) : (
                    <div className="flex gap-2 text-on-surface-variant">
                      {!isDone && (
                         <>
                           {isRunning ? (
                             <button onClick={() => pauseTask()} className="hover:text-primary transition-colors text-label-sm font-bold border border-primary px-2 rounded">Pause</button>
                           ) : isPaused ? (
                             <button onClick={() => resumeTask()} className="hover:text-primary transition-colors text-label-sm font-bold border border-primary px-2 rounded">Resume</button>
                           ) : (
                             <button onClick={() => startTask(task)} className="hover:text-primary transition-colors text-label-sm font-bold border border-outline-variant hover:border-primary px-2 rounded">Start</button>
                           )}
                         </>
                      )}
                      <button onClick={() => startEdit(task)} className="hover:text-primary transition-colors" title="Edit">
                        <span className="material-symbols-outlined text-[20px]">edit</span>
                      </button>
                      <button onClick={() => confirmDelete(task.id)} className="hover:text-error transition-colors" title="Delete">
                        <span className="material-symbols-outlined text-[20px]">delete</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}