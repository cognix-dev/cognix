# NEON TETRIS EXTREME

## Overview
Build an ultra-polished Tetris game called "NEON TETRIS" with explosive cyberpunk aesthetics and over-the-top visual effects.

## Technical Requirements
- Pure HTML + CSS + JS (no frameworks)
- Single HTML file OR separate files (HTML/CSS/JS)
- Canvas for game rendering
- requestAnimationFrame for smooth 60fps
- Particle system: Object pool for performance (max 500 particles)
- LocalStorage for high score persistence
- Responsive: Scales proportionally for smaller screens

## Core Visual Identity

### Background
- Animated deep space (#050510) with:
  - Slow-moving grid lines (cyan, parallax scrolling upward)
  - Distant floating particles (tiny cyan/pink dots, drifting)
  - Subtle scanline overlay (CRT retro effect, very faint)
  - Vignette (darker edges)

### Color Palette
- Cyan: #00f5ff
- Hot Pink: #ff2bbf
- Purple: #8b5cf6
- Electric Blue: #3b82f6
- Emerald: #10b981
- Red: #f43f5e
- Orange: #f97316

## Block Design (MAXIMUM GLOW)

Each tetromino piece:
- I-piece: Cyan (#00f5ff) with bright white core
- O-piece: Hot Pink (#ff2bbf)
- T-piece: Purple (#8b5cf6)
- S-piece: Emerald (#10b981)
- Z-piece: Red (#f43f5e)
- J-piece: Blue (#3b82f6)
- L-piece: Orange (#f97316)

Block rendering (for each cell):
- Inner gradient (lighter center to darker edge)
- Outer glow: 20px blur in block's color
- Subtle inner border (white, 10% opacity)
- When moving: Motion blur trail (3 ghost images, fading)

## Layout
- Center: Game board (10×20), 30px per cell, total 300×600
- Right panel (240px): HUD with glassmorphism cards
- Header: Large "NEON TETRIS" title with animated glow pulse
- Background behind board: Subtle blue gradient spotlight

## HUD Panel (Right Side)

All cards have glassmorphism (blur, transparency, gradient border):

### 1. SCORE Card
- Large number with counting animation
- Glows brighter when score increases
- Format: 000,000

### 2. LEVEL Card
- Current level (starts at 1)
- Progress bar to next level (fills as lines clear)
- Pulses when level up

### 3. LINES Card
- Total lines cleared
- Small "+X" popup when lines clear

### 4. NEXT Card
- 4×4 preview grid
- Next piece shown with full glow effects
- Subtle rotation animation (piece slowly spins)

### 5. COMBO Card (appears during combos)
- Shows current combo multiplier: "x2", "x3", etc.
- Larger and more intense glow with higher combo
- Shakes at x4+

### 6. HIGH SCORE Card
- Stored in localStorage
- Crown icon if current score beats it
- "NEW RECORD!" animation

## Visual Effects

### Line Clear Effects

#### Single Line (1 line)
- White flash on cleared row
- Row explodes into particles (block color)
- Small screen shake (2px, 100ms)
- Particles: 20-30 per block, scatter with gravity

#### Double (2 lines)
- All of Single effects, plus:
- Lightning bolt strikes down through cleared rows
- Bigger particle burst

#### Triple (3 lines)
- All of Double effects, plus:
- Screen flash (white, 50ms)
- Slow motion effect (0.5x speed for 300ms)
- Electric arcs between cleared rows

#### TETRIS (4 lines) - THE BIG ONE
- Full screen white flash (100ms)
- "TETRIS!" text slams onto screen (huge, cyan glow, shakes)
- Rainbow wave ripples across board
- Maximum slow motion (0.3x for 500ms)
- Explosion particles from all 4 rows
- Screen shake (5px, 300ms)
- All remaining blocks briefly pulse
- Background grid intensifies color

### Combo System Effects
- Combo counter appears on successful back-to-back clears
- x2: Cyan glow
- x3: Green glow + slight shake
- x4: Orange glow + continuous shake
- x5+: Pink/magenta glow + intense shake + "UNSTOPPABLE!" text

### Hard Drop Effect
- Piece leaves vertical light trail as it drops
- Impact shockwave (circular, expands outward)
- Small dust particles at landing spot
- Brief camera push (zoom in 2%, snap back)

### Level Up Sequence
- "LEVEL UP!" text zooms in with glow
- Background grid color shifts (more intense)
- All HUD cards pulse
- Speed increase is visible (drop interval shortens)
- New level number slams into HUD card

### Game Over Sequence
- Pieces gray out from bottom to top (wave effect)
- Each row makes small explosion as it grays
- Slow zoom out effect
- "GAME OVER" fades in (large, red glow)
- Final stats appear one by one:
  - Score: [animated count up]
  - Lines: [value]
  - Level: [value]
  - Best Combo: [value]
- If high score: "NEW HIGH SCORE!" with fireworks
- "Press ENTER to restart" pulses at bottom

### Start Screen
- "NEON TETRIS" title with electric flicker effect
- Subtitle "CYBERPUNK EDITION" types out letter by letter
- Background: Demo tetris playing itself (AI)
- "PRESS ENTER TO START" pulses
- High score displayed

### Pause Screen
- Game board blurs
- "PAUSED" with glitch effect
- "Press P to resume"

## Gameplay Mechanics
- Standard Tetris: 10×20 board
- 7 tetrominoes with standard rotations
- Wall kicks enabled
- Ghost piece enabled
- Soft drop: Arrow Down (1 point per cell)
- Hard drop: Space (2 points per cell)
- Move: Arrow Left/Right
- Rotate: Arrow Up (clockwise)
- Pause: P

## Scoring
- Single: 100 × level
- Double: 300 × level
- Triple: 500 × level
- Tetris: 800 × level
- Combo multiplier: x1, x1.5, x2, x2.5, x3...
- Soft drop: 1 point per cell
- Hard drop: 2 points per cell

## Speed Progression
- Level 1: 1000ms
- Level 2: 925ms
- Level 3: 850ms
- ... (−75ms per level)
- Level 13+: 100ms (max speed)
- Level up every 10 lines

## Audio (Web Audio API - simple, impactful)
- Move: Short blip
- Rotate: Higher blip
- Soft drop: Whoosh
- Hard drop: Heavy impact thud
- Line clear: Satisfying "ding" (pitch increases with more lines)
- Tetris: Epic synth chord + explosion sound
- Combo: Rising tone with each combo level
- Level up: Triumphant fanfare (short)
- Game over: Descending dramatic tone
- Optional: Background music toggle (simple synthwave loop)

## Performance Considerations
- Particle count limit with object pooling
- Efficient collision detection
- RequestAnimationFrame-based game loop
- Canvas optimization (dirty rect rendering if needed)

## File Output
- Single file: `neon_tetris.html`
- No external resources
- Works in modern browsers (Chrome, Firefox, Safari, Edge)
