# Design System Quick Reference Guide

## 🎯 Using the Design System in Dashboard Pages

### Metric Cards (Fixed 120px Height)

**HTML Structure**:
```html
<div class="metric-card">
  <div class="metric-label">Label Text</div>
  <div class="metric-value">$12,345</div>
  <div class="metric-delta positive">+5.32%</div>
</div>
```

**With Status Colors**:
```html
<div class="metric-card success">...</div>  <!-- Green accent -->
<div class="metric-card danger">...</div>   <!-- Red accent -->
<div class="metric-card warning">...</div>  <!-- Yellow accent -->
<div class="metric-card info">...</div>     <!-- Blue accent -->
```

### Responsive Layouts

**4-Column Grid (Desktop)**:
```html
<div class="row gap-3">
  <div class="col-lg-3 col-md-6 col-xs-12">Card 1</div>
  <div class="col-lg-3 col-md-6 col-xs-12">Card 2</div>
  <div class="col-lg-3 col-md-6 col-xs-12">Card 3</div>
  <div class="col-lg-3 col-md-6 col-xs-12">Card 4</div>
</div>
```

**Gaps Available**: `gap-1`, `gap-2`, `gap-3`, `gap-4`, `gap-5`

### Text Colors

```html
<p class="text-primary">Primary text</p>
<p class="text-secondary">Secondary text</p>
<p class="text-success">Success state</p>
<p class="text-danger">Danger state</p>
<p class="text-warning">Warning state</p>
<p class="text-info">Info state</p>
```

### Spacing Classes

**Margin**: `m-1` to `m-5`, `mt-X`, `mb-X`, `ml-X`, `mr-X`  
**Padding**: `p-1` to `p-5`, `px-X`, `py-X`  

**Example**:
```html
<div class="mt-4 mb-3 px-5">Content</div>
```

### Buttons

```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-success">Success</button>
<button class="btn btn-sm">Small Button</button>
<button class="btn btn-lg">Large Button</button>
<button class="btn btn-outline-primary">Outline</button>
<button class="btn btn-ghost">Ghost</button>
```

### Status Indicators

```html
<div class="status-indicator">
  <span class="status-dot online"></span> Online
</div>
<div class="status-indicator">
  <span class="status-dot warning"></span> Warning
</div>
```

### Badges

```html
<span class="badge badge-success">Active</span>
<span class="badge badge-danger">Failed</span>
<span class="badge badge-info">Info</span>
```

### Alerts

```html
<div class="alert alert-success">
  Success message
  <button class="alert-close">&times;</button>
</div>
<div class="alert alert-danger">Error message</div>
<div class="alert alert-warning">Warning message</div>
```

### Flexbox Layout

```html
<div class="d-flex justify-content-between align-items-center gap-3">
  <span>Left</span>
  <span>Right</span>
</div>

<div class="d-flex flex-column gap-2">
  <span>Item 1</span>
  <span>Item 2</span>
</div>
```

### Sizing

```html
<div class="w-50">50% width</div>
<div class="w-100">Full width</div>
<div class="h-100">Full height</div>
<div class="min-h-screen">Full viewport height</div>
```

### Shadows

```html
<div class="shadow-sm">Light shadow</div>
<div class="shadow-md">Medium shadow</div>
<div class="shadow-lg">Large shadow</div>
<div class="shadow-xl">Extra large shadow</div>
```

### Border Radius

```html
<div class="rounded">Default radius (6px)</div>
<div class="rounded-lg">Large radius (8px)</div>
<div class="rounded-xl">Extra large (12px)</div>
<div class="rounded-full">Full round</div>
```

### Text Utilities

```html
<p class="text-uppercase">UPPERCASE TEXT</p>
<p class="text-center">Centered text</p>
<p class="text-truncate">Truncated text with ellipsis...</p>
<p class="font-weight-bold">Bold text</p>
<p class="line-height-relaxed">Text with increased line height</p>
```

### Display Utilities

```html
<div class="d-none">Hidden</div>
<div class="d-block">Block display</div>
<div class="overflow-hidden">Hidden overflow</div>
<div class="overflow-auto">Scrollable</div>
```

### Tables

```html
<table class="table table-striped">
  <thead>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Data 1</td>
      <td>Data 2</td>
    </tr>
  </tbody>
</table>
```

### Cards

```html
<div class="card">
  <div class="card-header">Card Title</div>
  <div class="card-body">
    Card content here
  </div>
  <div class="card-footer">Footer text</div>
</div>
```

### Forms

```html
<div class="form-group">
  <label>Username</label>
  <input type="text" class="form-control" placeholder="Enter username">
</div>

<div class="form-check">
  <input type="checkbox" id="check1">
  <label for="check1">Remember me</label>
</div>

<select class="form-control">
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

---

## 🎨 CSS Variables Reference

### Spacing
```css
var(--spacing-xs)    /* 4px */
var(--spacing-sm)    /* 8px */
var(--spacing-md)    /* 16px */
var(--spacing-lg)    /* 24px */
var(--spacing-xl)    /* 32px */
var(--spacing-2xl)   /* 48px */
var(--spacing-3xl)   /* 64px */
```

### Colors
```css
var(--primary-color)      /* #ff914d */
var(--success-color)      /* #27ae60 */
var(--danger-color)       /* #e74c3c */
var(--warning-color)      /* #f39c12 */
var(--info-color)         /* #3498db */
```

### Shadows
```css
var(--shadow-sm)
var(--shadow-md)
var(--shadow-lg)
var(--shadow-xl)
var(--shadow-2xl)
```

### Transitions
```css
var(--transition-fast)   /* 150ms */
var(--transition-base)   /* 200ms */
var(--transition-slow)   /* 300ms */
```

### Radius
```css
var(--radius-xs)    /* 2px */
var(--radius-sm)    /* 4px */
var(--radius-md)    /* 6px */
var(--radius-lg)    /* 8px */
var(--radius-xl)    /* 12px */
var(--radius-full)  /* 9999px */
```

---

## 📱 Responsive Breakpoints

### Targeting Specific Breakpoints

**Mobile Only** (375-767px):
```css
@media (max-width: 767px) {
  /* Mobile styles */
}
```

**Tablet and Up** (768px+):
```css
@media (min-width: 768px) {
  /* Tablet and larger */
}
```

**Desktop Only** (1024-1439px):
```css
@media (min-width: 1024px) and (max-width: 1439px) {
  /* Desktop styles */
}
```

**Large Desktop and Up** (1440px+):
```css
@media (min-width: 1440px) {
  /* Large desktop */
}
```

**4K Displays** (1920px+):
```css
@media (min-width: 1920px) {
  /* 4K styles */
}
```

### Responsive Classes

**Mobile Grid**:
```html
<div class="col-xs-6">50% width on mobile</div>
<div class="col-xs-12">Full width on mobile</div>
```

**Tablet Grid**:
```html
<div class="col-sm-6">50% width on tablet</div>
<div class="col-sm-12">Full width on tablet</div>
```

**Desktop Grid**:
```html
<div class="col-md-3">25% width</div>
<div class="col-lg-3">25% width on large desktop</div>
<div class="col-xl-3">25% width on 4K</div>
```

---

## 🔧 Common Patterns

### Centered Content Box
```html
<div class="d-flex justify-content-center align-items-center min-h-screen">
  <div class="w-50">Centered content</div>
</div>
```

### Metric Cards Row
```html
<div class="row gap-3">
  <div class="col-lg-3 col-md-6 col-xs-12">
    <div class="metric-card">
      <div class="metric-label">Total Value</div>
      <div class="metric-value">$50,000</div>
      <div class="metric-delta positive">+10%</div>
    </div>
  </div>
  <!-- Repeat for other cards -->
</div>
```

### Card with Header and Footer
```html
<div class="card">
  <div class="card-header">Transactions</div>
  <div class="card-body">
    <table class="table table-striped">
      <!-- Table content -->
    </table>
  </div>
  <div class="card-footer">
    Showing 1-10 of 100 items
  </div>
</div>
```

### Data Section with Alert
```html
<div class="p-4 mb-4">
  <h2>Market Data</h2>
  
  <div class="alert alert-warning mb-4">
    <span>⚠️</span>
    <span>Market volatility detected</span>
  </div>
  
  <div class="row gap-3">
    <!-- Metric cards -->
  </div>
</div>
```

### Button Group
```html
<div class="d-flex gap-2">
  <button class="btn btn-primary flex-grow-1">Save</button>
  <button class="btn btn-ghost flex-grow-1">Cancel</button>
</div>
```

---

## 📊 Dashboard Integration Examples

### Portfolio Page
```python
html.Div([
    html.H2("Portfolio Overview", className="mb-4"),
    html.Div([
        # 4 metric cards in a responsive grid
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.Div("Total Value", className="metric-label"),
                    html.Div(f"${total_value}", className="metric-value"),
                ], className="metric-card"),
                lg=3, md=6, xs=12
            ),
            # ... more cards
        ], className="gap-3 mb-4")
    ], className="p-4")
], className="container")
```

### Alert with Status
```python
dbc.Alert([
    "⚠️ Portfolio P&L is negative",
], color="warning", className="mb-4")
```

---

## ✅ Best Practices

1. **Use Design Tokens**: Always use CSS variables instead of hardcoding colors/spacing
2. **Responsive First**: Design mobile-first, then enhance for larger screens
3. **Consistent Spacing**: Use the 8px baseline grid for all spacing
4. **Color Semantics**: Use success/danger/warning/info for status and state
5. **Accessibility**: Always include focus states and proper contrast ratios
6. **Transitions**: Add smooth transitions for interactive elements
7. **Testing**: Test all breakpoints (375px, 768px, 1024px, 1440px, 1920px)

---

**Design System Version**: 1.0  
**Last Updated**: Today  
**Status**: ✅ Active & Deployed  
