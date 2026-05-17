---
name: Quiet Editorial
colors:
  surface: '#fdf8f5'
  surface-dim: '#ddd9d6'
  surface-bright: '#fdf8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3ef'
  surface-container: '#f2ede9'
  surface-container-high: '#ece7e4'
  surface-container-highest: '#e6e2de'
  on-surface: '#1c1b19'
  on-surface-variant: '#55433d'
  inverse-surface: '#32302e'
  inverse-on-surface: '#f4f0ec'
  outline: '#88726c'
  outline-variant: '#dbc1b9'
  surface-tint: '#99462a'
  primary: '#99462a'
  on-primary: '#ffffff'
  primary-container: '#d97757'
  on-primary-container: '#541400'
  inverse-primary: '#ffb59e'
  secondary: '#5f5f58'
  on-secondary: '#ffffff'
  secondary-container: '#e4e2da'
  on-secondary-container: '#65655e'
  tertiary: '#006b5f'
  on-tertiary: '#ffffff'
  tertiary-container: '#09a493'
  on-tertiary-container: '#00312b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59e'
  on-primary-fixed: '#390b00'
  on-primary-fixed-variant: '#7a2f15'
  secondary-fixed: '#e4e2da'
  secondary-fixed-dim: '#c8c7bf'
  on-secondary-fixed: '#1b1c17'
  on-secondary-fixed-variant: '#474741'
  tertiary-fixed: '#7df7e3'
  tertiary-fixed-dim: '#5edac7'
  on-tertiary-fixed: '#00201c'
  on-tertiary-fixed-variant: '#005047'
  background: '#fdf8f5'
  on-background: '#1c1b19'
  surface-variant: '#e6e2de'
typography:
  headline-xl:
    fontFamily: Newsreader
    fontSize: 48px
    fontWeight: '500'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 32px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '500'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Newsreader
    fontSize: 20px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Newsreader
    fontSize: 17px
    fontWeight: '400'
    lineHeight: '1.6'
  label-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 720px
  gutter: 24px
  margin-mobile: 20px
  margin-desktop: 40px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
---

## Brand & Style

This design system is built upon a philosophy of intellectual calm and focused clarity. It draws inspiration from high-end editorial publishing and academic journals, prioritizing the reading experience over visual noise. The aesthetic is "Quiet and Editorial," characterized by a "paper-like" digital presence that feels tactile yet modern.

The design system avoids the frantic energy of typical tech interfaces in favor of a deliberate, slower pace. It utilizes a minimalist approach where the quality of typography and the rhythm of whitespace do the heavy lifting. The goal is to evoke a sense of trust, thoughtfulness, and professional maturity, positioning the product as a tool for deep work rather than shallow engagement.

## Colors

The palette is rooted in natural, desaturated tones to reduce eye strain and promote focus. 

- **Background (Claude Cream):** A warm, off-white base that mimics premium book paper.
- **Text (Charcoal Ink):** High-contrast but softer than pure black, ensuring legibility without harshness.
- **Surface/Dividers (Soft Sand):** Used for input fields, hair-thin dividers, and subtle containers to create structure without adding weight.
- **Accent (Terracotta):** Reserved strictly for primary calls to action or essential status indicators. Its usage must be sparse to maintain its impact and the overall "quiet" nature of the UI.

## Typography

This design system employs a dual-typeface strategy to distinguish between content and utility.

**Newsreader** is the primary voice. It is used for all narrative content, headlines, and long-form reading. Its humanist serif qualities provide the "academic" feel and high readability essential for the brand.

**Inter** is the functional workhorse. It is used exclusively for the UI "chrome"—buttons, labels, input hints, and navigation. This clear distinction helps users subconsciously separate the tool they are using from the content they are consuming.

Typesetting should favor generous line heights (1.6x for body text) and optimized measure (maximum line lengths of 65-75 characters) to ensure a comfortable reading experience.

## Layout & Spacing

The layout philosophy centers on a **Fixed Reading Grid**. While the UI containers may scale, the primary content column is capped at 720px to prevent line lengths from becoming unreadable on wide displays.

The spacing rhythm uses a 4px base unit, favoring larger "Stack" values to create breathable, airy layouts. 
- **Desktop:** Centralized content with generous side margins (40px+) and significant vertical separation between sections.
- **Mobile:** Margins compress to 20px, and typography scales down slightly to maintain hierarchy without feeling cramped.
- **Alignment:** Consistent left-alignment is preferred for all content to mimic traditional manuscript layouts.

## Elevation & Depth

Depth in this design system is achieved through **Tonal Layering** rather than shadows. The UI remains flat to maintain its "printed paper" aesthetic.

- **Level 0 (Base):** The Claude Cream background.
- **Level 1 (Surfaces):** Soft Sand used for cards or secondary navigation bars. 
- **Dividers:** Instead of shadows, use "hair-thin" 1px dividers in Soft Sand or a 5% darker tint of the background to separate sections.
- **Interactions:** Subtle background color shifts (e.g., Cream to a slightly darker tint) indicate hover states. Shadow use is strictly prohibited except for critical floating elements like modals, where a very soft, diffused, and low-opacity neutral shadow may be applied.

## Shapes

The shape language is "Softly Geometric." A standard radius of 8px (Level 2) is applied to buttons and input fields to make the interface feel approachable and modern without appearing "bubbly" or childish.

Large cards or container blocks may use larger radii (16px - 24px) to emphasize a soft, paper-like corner. Dividers should always be sharp (0px) to maintain a clean, architectural line.

## Components

### Buttons
- **Primary:** Flat Terracotta background with White or Cream text. No borders. 8px radius.
- **Secondary:** Flat Soft Sand background with Charcoal Ink text.
- **Ghost:** No background, Charcoal Ink text, underlined only on hover.

### Input Fields
- **Style:** Background in Soft Sand. No border, or a 1px border that matches the background color slightly darkened.
- **Focus State:** A subtle 1px border in Terracotta or a slightly darker Sand tint. No outer glow.

### Cards
- **Style:** Flat. Defined by either a 1px Soft Sand border or a subtle shift in background color. No shadows.

### Dividers
- **Style:** 1px solid lines using Soft Sand. Used horizontally to separate content sections or vertically to separate navigation from main content.

### Lists
- **Style:** Clean, no bullet points for primary navigation. Use generous vertical padding (16px) between list items to maintain the "Quiet" aesthetic.

### Chips/Tags
- **Style:** Small 13px Inter font. Soft Sand background with Charcoal Ink text. High roundedness (pill-shaped) to distinguish them from actionable buttons.