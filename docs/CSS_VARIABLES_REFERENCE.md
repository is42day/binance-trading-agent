# Design System CSS Variables Reference

Complete reference of all CSS custom properties (variables) available in the Binance Trading Agent Dashboard design system.

---

## Spacing Variables (8px Baseline Grid)

```css
--spacing-xs:    0.25rem;   /* 4px */
--spacing-sm:    0.5rem;    /* 8px */
--spacing-md:    1rem;      /* 16px */
--spacing-lg:    1.5rem;    /* 24px */
--spacing-xl:    2rem;      /* 32px */
--spacing-2xl:   3rem;      /* 48px */
--spacing-3xl:   4rem;      /* 64px */
```

**Usage**:
```css
padding: var(--spacing-md);          /* 16px */
margin-bottom: var(--spacing-lg);    /* 24px */
gap: var(--spacing-sm);              /* 8px */
```

---

## Border Radius Variables

```css
--radius-xs:     2px;
--radius-sm:     4px;
--radius-md:     6px;
--radius-lg:     8px;
--radius-xl:     12px;
--radius-full:   9999px;    /* Circular */
```

**Usage**:
```css
border-radius: var(--radius-lg);     /* 8px */
border-radius: var(--radius-full);   /* Circular */
```

---

## Shadow Depths

```css
--shadow-sm:     0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md:     0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-lg:     0 8px 16px rgba(0, 0, 0, 0.15);
--shadow-xl:     0 12px 24px rgba(0, 0, 0, 0.2);
--shadow-2xl:    0 20px 48px rgba(0, 0, 0, 0.3);
--shadow-glow:   0 0 32px rgba(255, 145, 77, 0.2);
```

**Usage**:
```css
box-shadow: var(--shadow-md);        /* Standard */
box-shadow: var(--shadow-lg);        /* Elevated */
box-shadow: var(--shadow-glow);      /* Orange glow */
```

---

## Transition Timings

```css
--transition-fast:  150ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-base:  200ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-slow:  300ms cubic-bezier(0.4, 0, 0.2, 1);
```

**Usage**:
```css
transition: all var(--transition-base);     /* 200ms */
transition: background-color var(--transition-fast);  /* 150ms */
```

---

## Z-Index Scale

```css
--z-base:        1;
--z-dropdown:    1000;
--z-sticky:      1010;
--z-fixed:       1020;
--z-modal:       1040;
--z-tooltip:     1070;
```

**Usage**:
```css
z-index: var(--z-dropdown);    /* Dropdowns */
z-index: var(--z-modal);       /* Modals */
position: sticky; z-index: var(--z-sticky);  /* Sticky elements */
```

---

## Primary Color Palette

```css
--primary-color:    #ff914d;   /* Base orange */
--primary-light:    #ffb974;   /* Lighter shade */
--primary-lighter:  #ffc89a;   /* Lightest shade */
--primary-dark:     #e67e22;   /* Darker shade */
--primary-darker:   #cc6b11;   /* Darkest shade */
```

**Usage**:
```css
background-color: var(--primary-color);
color: var(--primary-light);
border-color: var(--primary-dark);
```

**RGB Values** (for transparency):
```css
rgba(255, 145, 77, 0.1)   /* 10% opacity */
rgba(255, 145, 77, 0.2)   /* 20% opacity */
rgba(255, 145, 77, 0.3)   /* 30% opacity */
```

---

## Semantic Color Palette

### Success (Green)
```css
--success-color:    #27ae60;   /* Primary green */
--success-light:    #46c474;   /* Light green */
--success-dark:     #1e8449;   /* Dark green */
```

### Danger (Red)
```css
--danger-color:     #e74c3c;   /* Primary red */
--danger-light:     #ec7063;   /* Light red */
--danger-dark:      #c0392b;   /* Dark red */
```

### Warning (Yellow)
```css
--warning-color:    #f39c12;   /* Primary yellow */
--warning-light:    #f5b041;   /* Light yellow */
--warning-dark:     #d68910;   /* Dark yellow */
```

### Info (Blue)
```css
--info-color:       #3498db;   /* Primary blue */
--info-light:       #5dade2;   /* Light blue */
--info-dark:        #2874a6;   /* Dark blue */
```

**Usage**:
```css
/* Success (positive change) */
color: var(--success-color);
background-color: rgba(39, 174, 96, 0.1);

/* Danger (negative change) */
color: var(--danger-color);
background-color: rgba(231, 76, 60, 0.1);

/* Warning (alerts) */
color: var(--warning-color);
background-color: rgba(243, 156, 18, 0.1);

/* Info (information) */
color: var(--info-color);
background-color: rgba(52, 152, 219, 0.1);
```

---

## Neutral Color Scale

```css
--neutral-50:   #f8f9fa;    /* Very light */
--neutral-100:  #e9ecef;
--neutral-200:  #dee2e6;
--neutral-300:  #ced4da;
--neutral-400:  #adb5bd;
--neutral-500:  #6c757d;    /* Mid gray */
--neutral-600:  #495057;
--neutral-700:  #343a40;
--neutral-800:  #212529;
--neutral-900:  #111827;    /* Very dark */
```

---

## Dark Theme Colors

```css
--bg-dark:      #1a1d23;       /* Primary background */
--bg-darker:    #0f1117;       /* Secondary background */
--bg-card:      #23242a;       /* Card background */
--bg-hover:     rgba(255, 145, 77, 0.05);   /* Hover state */
--bg-active:    rgba(255, 145, 77, 0.1);    /* Active state */

--text-primary:      #f4f2ee;   /* Main text */
--text-secondary:    #b8b4b0;   /* Secondary text */
--text-tertiary:     #8a8580;   /* Tertiary text */
--text-inverse:      #1a1d23;   /* Text on light backgrounds */

--border-color:      rgba(255, 145, 77, 0.2);   /* Subtle border */
--border-light:      rgba(255, 145, 77, 0.1);   /* Very subtle */
--border-dark:       rgba(255, 145, 77, 0.3);   /* More prominent */
```

**Usage**:
```css
/* Background */
background-color: var(--bg-card);

/* Text */
color: var(--text-primary);

/* Borders */
border: 1px solid var(--border-color);

/* Hover effects */
background-color: var(--bg-hover);
```

---

## Responsive Breakpoints

```css
--breakpoint-xs:   375px;   /* Mobile */
--breakpoint-sm:   768px;   /* Tablet */
--breakpoint-md:   1024px;  /* Desktop */
--breakpoint-lg:   1440px;  /* Large desktop */
--breakpoint-xl:   1920px;  /* 4K displays */
```

**Media Query Syntax**:
```css
/* Mobile */
@media (max-width: 767px) { }

/* Tablet and up */
@media (min-width: 768px) { }

/* Desktop and up */
@media (min-width: 1024px) { }

/* Large desktop and up */
@media (min-width: 1440px) { }

/* 4K and up */
@media (min-width: 1920px) { }
```

---

## Complete Variable Usage Examples

### Example 1: Card Component
```css
.card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-base);
}

.card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

.card-header {
    background-color: var(--bg-darker);
    border-bottom: 2px solid var(--primary-color);
    padding: var(--spacing-md) var(--spacing-lg);
}

.card-body {
    padding: var(--spacing-lg);
    color: var(--text-primary);
}
```

### Example 2: Button Component
```css
.btn-primary {
    background-color: var(--primary-color);
    color: white;
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--radius-md);
    min-height: 44px;
    transition: all var(--transition-base);
    box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
    background-color: var(--primary-light);
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

.btn-primary:active {
    box-shadow: var(--shadow-md);
    transform: translateY(0);
}
```

### Example 3: Metric Card
```css
.metric-card {
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-darker) 100%);
    border: 1px solid var(--border-color);
    border-left: 4px solid var(--primary-color);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    min-height: 120px;
    box-shadow: var(--shadow-md);
    transition: all var(--transition-base);
}

.metric-card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
    border-left-color: var(--primary-light);
}

.metric-label {
    color: var(--text-secondary);
    font-size: 0.75rem;
    margin-bottom: var(--spacing-xs);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value {
    color: var(--text-primary);
    font-size: 1.75rem;
    font-weight: 800;
}

.metric-delta.positive {
    color: var(--success-color);
}

.metric-delta.negative {
    color: var(--danger-color);
}
```

### Example 4: Alert Component
```css
.alert {
    padding: var(--spacing-md) var(--spacing-lg);
    border-radius: var(--radius-lg);
    border: 1px solid;
    margin-bottom: var(--spacing-lg);
}

.alert-success {
    background-color: rgba(39, 174, 96, 0.08);
    border-color: var(--success-color);
    color: var(--success-color);
}

.alert-danger {
    background-color: rgba(231, 76, 60, 0.08);
    border-color: var(--danger-color);
    color: var(--danger-color);
}

.alert-warning {
    background-color: rgba(243, 156, 18, 0.08);
    border-color: var(--warning-color);
    color: var(--warning-color);
}
```

### Example 5: Form Input
```css
.form-control {
    background-color: var(--bg-darker);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    min-height: 44px;
    transition: all var(--transition-base);
}

.form-control:hover:not(:focus) {
    border-color: var(--border-dark);
}

.form-control:focus {
    background-color: var(--bg-card);
    border-color: var(--primary-color);
    outline: none;
    box-shadow: 0 0 0 3px rgba(255, 145, 77, 0.1);
}
```

### Example 6: Responsive Container
```css
.container {
    width: 100%;
    padding: var(--spacing-xl) var(--spacing-lg);
}

@media (min-width: 768px) {
    .container {
        max-width: 750px;
        padding: var(--spacing-xl) var(--spacing-lg);
    }
}

@media (min-width: 1024px) {
    .container {
        max-width: 1000px;
        padding: var(--spacing-xl) var(--spacing-lg);
    }
}

@media (min-width: 1440px) {
    .container {
        max-width: 1340px;
        padding: var(--spacing-2xl) var(--spacing-xl);
    }
}

@media (min-width: 1920px) {
    .container {
        max-width: 1800px;
        padding: var(--spacing-2xl) var(--spacing-2xl);
    }
}
```

---

## Variable Organization Hierarchy

```
CSS Variables
├── Spacing (7 levels)
├── Border Radius (6 sizes)
├── Shadows (6 depths)
├── Transitions (3 speeds)
├── Z-Index (6 layers)
├── Primary Color (5 variants)
├── Semantic Colors (4 types × 3 variants = 12 colors)
├── Neutral Scale (9 levels)
├── Dark Theme (8 variables)
└── Breakpoints (5 ranges)

Total: 70+ CSS Custom Properties
```

---

## Best Practices for Using Variables

### 1. Always Use Variables
```css
/* ✅ Good */
padding: var(--spacing-md);
color: var(--text-primary);
border-radius: var(--radius-lg);

/* ❌ Avoid */
padding: 16px;
color: #f4f2ee;
border-radius: 8px;
```

### 2. Semantic Color Usage
```css
/* ✅ Good - Uses semantic colors appropriately */
.success-indicator {
    color: var(--success-color);
}

.error-message {
    color: var(--danger-color);
}

/* ❌ Avoid - Hardcoded colors */
.success-indicator {
    color: #27ae60;
}
```

### 3. Responsive Spacing
```css
/* ✅ Good - Scales with breakpoints */
.card {
    padding: var(--spacing-lg);
}

@media (max-width: 767px) {
    .card {
        padding: var(--spacing-md);
    }
}

/* ❌ Avoid - Fixed values */
.card {
    padding: 24px;
}
```

### 4. Consistent Transitions
```css
/* ✅ Good - Uses transition variables */
.btn {
    transition: all var(--transition-base);
}

.btn:hover {
    transition: all var(--transition-fast);
}

/* ❌ Avoid - Inconsistent timings */
.btn {
    transition: all 0.3s ease;
}
```

---

## Common Variable Combinations

### Primary Action Button
```css
.btn-primary {
    background-color: var(--primary-color);
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--radius-md);
    transition: all var(--transition-base);
    box-shadow: var(--shadow-sm);
}
```

### Card with Metrics
```css
.metric-card {
    background-color: var(--bg-card);
    border-left: 4px solid var(--primary-color);
    padding: var(--spacing-lg);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    min-height: 120px;
}
```

### Input with Validation
```css
.form-control.is-valid {
    border-color: var(--success-color);
    box-shadow: 0 0 0 3px rgba(39, 174, 96, 0.1);
}

.form-control.is-invalid {
    border-color: var(--danger-color);
    box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
}
```

### Alert Component
```css
.alert-warning {
    background-color: rgba(243, 156, 18, 0.08);
    border: 1px solid var(--warning-color);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    color: var(--warning-color);
}
```

---

## Migration Guide (Updating Existing Code)

### Before (Hardcoded)
```css
.card {
    padding: 24px;
    background-color: #23242a;
    border: 1px solid rgba(255, 145, 77, 0.2);
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease;
}
```

### After (Using Variables)
```css
.card {
    padding: var(--spacing-lg);
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-base);
}
```

---

## Performance Tips

1. **Use CSS Variables Judiciously**: They're fast but not free
2. **Group Related Variables**: Keeps CSS organized
3. **Set Defaults**: Provide fallback values
4. **Use in Media Queries**: Variables work in MQs
5. **No JavaScript Needed**: All styling is pure CSS

---

## Browser Support

All CSS Custom Properties are supported in:
- ✅ Chrome 49+
- ✅ Firefox 31+
- ✅ Safari 9.1+
- ✅ Edge 15+
- ✅ iOS Safari 9.3+
- ✅ Android Browser 62+

**Internet Explorer**: Not supported (but target is modern browsers only)

---

**Reference Version**: 1.0  
**Design System Version**: 1.0  
**Last Updated**: Today  
**Status**: ✅ Complete  
