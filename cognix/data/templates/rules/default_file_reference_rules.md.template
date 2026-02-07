# File Reference Rules (Enhanced Edition v2.4)
# Cognix - Automatic File Reference Validation Rules

**Version:** 2.4.0  
**Last Updated:** 2026-01-13  
**Type:** Default Rules (System-provided)  
**New in v2.4:** Flask-Static-File-Paths rule (Critical) - Prevents broken CSS/JS in Flask apps

---

## Overview

This file defines rules for validating file references across different file types.
Rules are automatically applied during code generation based on detected file patterns.

**Rule Structure:**
- **Phase:** 1 (Basic), 2 (Extended), 3 (Advanced), 4 (Runtime Constraints)
- **Priority:** Critical, High, Medium, Low
- **Trigger:** Condition to activate the rule
- **Target:** Condition for target files
- **Prompt:** Text to inject into LLM prompt when rule is triggered

**Changelog:**
- v2.4.0 (2026-01-13): Added Flask-Static-File-Paths rule (Phase 1, Critical) - #1 cause of broken Flask apps
- v2.3.0 (2026-01-11): Added Runtime Constraints rules (Phase 4) - SQLAlchemy reserved words, Circular import prevention, Flask app context, Cross-platform packages
- v2.2.0 (2026-01-01): Added Next.js/Nuxt.js/Remix framework rules, Test file conventions, OpenAPI/TypeScript rules
- v2.1.0 (2025-12-22): Added Professional-UI-No-Emojis rule
- v2.0.0 (2025-12-04): Initial enhanced edition with Python/Node.js patterns

---

# Phase 1: Basic Rules (High Priority)

---

## Rule: Flask-Static-File-Paths

**Phase:** 1  
**Priority:** Critical  
**Trigger:** Flask project detected (from flask import Flask, Flask(__name__))  
**Target:** HTML files referencing CSS/JS/images

**Prompt:**
```
CRITICAL - Flask Static File Path Convention:

When generating HTML files for Flask projects, ALWAYS use absolute paths with /static/ prefix:

✅ CORRECT (Flask):
   <link rel="stylesheet" href="/static/css/styles.css">
   <script src="/static/js/app.js"></script>
   <img src="/static/images/logo.png">

❌ WRONG (Will cause 404 errors):
   <link rel="stylesheet" href="css/styles.css">
   <script src="js/app.js"></script>
   <img src="images/logo.png">

WHY THIS MATTERS:
1. Flask serves static files at /static/ URL path by default
2. When serving index.html via send_from_directory('static', 'index.html'),
   the browser URL is '/' (root), NOT '/static/'
3. Relative paths like 'css/styles.css' resolve from '/' → '/css/styles.css' (404!)
4. Absolute paths '/static/css/styles.css' always resolve correctly

DIRECTORY STRUCTURE:
   static/
     index.html        → served at URL '/'
     css/styles.css    → accessed at URL '/static/css/styles.css'
     js/app.js         → accessed at URL '/static/js/app.js'

FOR JINJA2 TEMPLATES (best practice):
   <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">

REMEMBER: Relative paths in Flask HTML = broken CSS/JS = unusable application
```

**Context:**
Flask's default static file serving uses the /static/ URL prefix. This is the #1 cause of broken Flask web applications - CSS and JavaScript files fail to load because of incorrect relative paths in HTML files.

---

## Rule: HTML-CSS-Reference

**Phase:** 1  
**Priority:** High  
**Trigger:** HTML files exist (*.html)  
**Target:** CSS files exist (*.css)

**Prompt:**
```
CRITICAL - HTML-CSS Reference Integrity:

When generating HTML files that coexist with CSS files, you MUST ensure proper reference integrity:

1. **List ALL CSS files**: If you generate multiple CSS files (e.g., reset.css, variables.css, components.css), the HTML file MUST reference ALL of them using <link rel="stylesheet" href="..."> tags.

2. **DO NOT consolidate references**: Do NOT assume CSS files will be consolidated into a single file (e.g., main.css or styles.css) unless explicitly instructed.

3. **Correct example**:
   Generated CSS files: css/reset.css, css/variables.css, css/components.css
   HTML must include:
   ```html
   <link rel="stylesheet" href="css/reset.css">
   <link rel="stylesheet" href="css/variables.css">
   <link rel="stylesheet" href="css/components.css">
   ```

4. **INCORRECT example** (DO NOT DO THIS):
   ```html
   <link rel="stylesheet" href="css/main.css">  <!-- This file does not exist! -->
   ```

5. **Reference order matters**: Reference CSS files in logical order (reset → variables → layout → components → theme).

VERIFY: Before completing generation, double-check that every CSS file you generate is referenced in the HTML file.
```

---

## Rule: HTML-JavaScript-Reference

**Phase:** 1  
**Priority:** High  
**Trigger:** HTML files exist (*.html)  
**Target:** JavaScript files exist (*.js, *.mjs)

**Prompt:**
```
CRITICAL - HTML-JavaScript Reference Integrity:

When generating HTML files that coexist with JavaScript files, you MUST ensure proper reference integrity:

1. **List ALL JavaScript files**: If you generate multiple JS files (e.g., app.js, utils.js, config.js), the HTML file MUST reference ALL of them using <script src="..."></script> tags.

2. **Module type**: Use <script type="module" src="..."></script> for ES6 modules, or plain <script src="..."></script> for traditional scripts.

3. **Correct example**:
   Generated JS files: js/app.js, js/utils.js
   HTML must include:
   ```html
   <script type="module" src="js/app.js"></script>
   <script type="module" src="js/utils.js"></script>
   ```

4. **Loading order**: If files have dependencies, ensure correct loading order (utilities first, then main app).

5. **Defer/Async**: Consider using defer or async attributes for non-blocking loading when appropriate.

VERIFY: Before completing generation, double-check that every JavaScript file you generate is referenced in the HTML file.
```

---

## Rule: React-Component-CSS-Import

**Phase:** 1  
**Priority:** High  
**Trigger:** React component files exist (*.jsx, *.tsx)  
**Target:** CSS files exist (*.css, *.module.css)

**Prompt:**
```
CRITICAL - React Component CSS Import Integrity:

When generating React components that coexist with CSS files, you MUST ensure proper import integrity:

1. **Import corresponding CSS**: If you create a component file (e.g., App.jsx) and a corresponding CSS file (e.g., App.css), the component MUST import its CSS.

2. **CSS Modules**: If using CSS Modules (*.module.css), import as: import styles from './Component.module.css'

3. **Correct example**:
   Generated files: src/components/TodoItem.jsx, src/components/TodoItem.css
   TodoItem.jsx must include:
   ```javascript
   import './TodoItem.css';
   ```

4. **Global CSS**: For global CSS files (e.g., index.css, App.css), import in the appropriate root component or index file.

5. **Import order**: Import CSS before component logic to ensure styles are loaded first.

VERIFY: Before completing generation, double-check that every CSS file has a corresponding import statement in the appropriate component.
```

---

## Rule: Professional-UI-No-Emojis

**Phase:** 1  
**Priority:** High  
**Trigger:** HTML files exist (*.html) OR React/Vue components exist (*.jsx, *.tsx, *.vue)  
**Target:** Any UI-related files

**Prompt:**
```
CRITICAL - Professional UI: No Emojis Policy

When generating user interfaces, NEVER use emojis unless explicitly requested by the user:

1. **NO emojis in UI text**: Do NOT use emojis (📝, ✏️, ❤️, 🎉, ✨, etc.) in any user-facing text:
   - Headings and titles
   - Button text
   - Labels and placeholders
   - Empty states and messages
   - Footer text
   - Error messages
   - Any other UI text

2. **WHY**: Emojis make applications look unprofessional and cheap. Professional applications use clean typography and proper iconography.

3. **Correct example** (Professional, clean UI):
   ```html
   <h1>My Todo List</h1>
   <button class="btn-add">Add Task</button>
   <p class="empty-text">No tasks yet. Add one to get started!</p>
   <footer>Built with HTML, CSS & JavaScript</footer>
   ```

4. **INCORRECT example** (Unprofessional, emoji-heavy):
   ```html
   <h1>📝 My Todo List</h1>
   <button class="btn-add">Add ✏️</button>
   <p class="empty-text">✨ No tasks yet. Add one to get started!</p>
   <footer>Built with ❤️ using vanilla JavaScript</footer>
   ```

5. **USE INSTEAD**:
   - SVG icons (preferred)
   - Icon fonts (Font Awesome, Material Icons, Heroicons)
   - Clean typography with proper styling
   - Professional unicode symbols (•, →, ✓, ×) for minimal decoration

6. **EXCEPTION**: Only use emojis if the user explicitly requests them:
   - "add emoji to the title"
   - "use 🎉 icon"
   - "include ❤️ symbol"
   
   If the request is ambiguous, default to NO emojis.

VERIFY: Before completing generation, scan all UI text and remove any emojis unless explicitly requested by the user.
```

---

# Phase 2: Extended Rules (Medium Priority)

---

## Rule: Python-Requirements-Import-Consistency

**Phase:** 2  
**Priority:** Medium  
**Trigger:** Python files exist (*.py)  
**Target:** requirements.txt exists

**Prompt:**
```
IMPORTANT - Python Requirements Consistency:

When generating Python files that use external libraries, ensure consistency with requirements.txt:

1. **Import statements must match requirements**: Every import statement for external libraries (e.g., import requests, import flask) must have a corresponding entry in requirements.txt.

2. **Version pinning**: Use specific versions in requirements.txt (e.g., requests==2.31.0) unless explicitly told to use loose versions.

3. **Correct example**:
   Python file imports: import requests, import pandas
   requirements.txt must include:
   ```
   requests==2.31.0
   pandas==2.1.0
   ```

4. **Exclude standard library**: Do NOT add standard library imports (e.g., os, sys, json) to requirements.txt.

5. **Check all Python files**: Scan ALL generated Python files for imports, not just the main file.

NOTE: This is a consistency check. If requirements.txt already exists, ensure new imports are added. If it doesn't exist, create it with all necessary dependencies.
```

---

## Rule: Package-JSON-Entry-Point-Consistency

**Phase:** 2  
**Priority:** Medium  
**Trigger:** package.json exists  
**Target:** JavaScript/TypeScript entry point files exist

**Prompt:**
```
IMPORTANT - Package.json Entry Point Consistency:

When generating a package.json with entry point specifications, ensure the entry point files exist:

1. **Main field**: If package.json has "main" field (e.g., "main": "index.js"), ensure index.js is generated.

2. **Scripts**: If package.json has scripts that reference files (e.g., "start": "node server.js"), ensure those files exist.

3. **Correct example**:
   package.json includes: "main": "src/index.js"
   You MUST generate: src/index.js

4. **Module field**: If package.json has "module" field, ensure ESM entry point exists.

5. **Type exports**: If package.json has "exports" field, ensure all referenced files exist.

NOTE: Missing entry points will cause npm/yarn commands to fail.
```

---

## Rule: TypeScript-Type-Declaration-Consistency

**Phase:** 2  
**Priority:** Medium  
**Trigger:** TypeScript files exist (*.ts, *.tsx)  
**Target:** tsconfig.json exists

**Prompt:**
```
IMPORTANT - TypeScript Configuration Consistency:

When generating TypeScript files, ensure consistency with tsconfig.json:

1. **Module system**: Match import/export style with tsconfig "module" setting.
   - "module": "ESNext" → use import/export
   - "module": "CommonJS" → use require/module.exports

2. **Strict mode**: If "strict": true, ensure:
   - No implicit any
   - Proper null checks
   - Explicit return types for functions

3. **Path aliases**: If paths are configured in tsconfig.json:
   ```json
   "paths": { "@/*": ["./src/*"] }
   ```
   Use the alias in imports: `import { Button } from '@/components/Button'`

4. **Declaration files**: If "declaration": true, expect .d.ts files to be generated.

NOTE: Mismatched configuration will cause compilation errors.
```

---

## Rule: Vue-Component-Structure

**Phase:** 2  
**Priority:** Medium  
**Trigger:** Vue files exist (*.vue)  
**Target:** Vue Single File Components

**Prompt:**
```
IMPORTANT - Vue Component Structure:

When generating Vue Single File Components, follow proper structure:

1. **Standard structure**: Every .vue file should have:
   ```vue
   <template>
     <!-- HTML template -->
   </template>

   <script setup>
   // or <script> for Options API
   </script>

   <style scoped>
   /* CSS styles */
   </style>
   ```

2. **Script setup (Vue 3)**: Prefer `<script setup>` for Composition API.

3. **Scoped styles**: Use `<style scoped>` to prevent style leakage.

4. **Props typing**: Define props with TypeScript or runtime validation.

5. **Component imports**: Import child components at the top of script.

NOTE: Following Vue conventions ensures proper reactivity and component behavior.
```

---

## Rule: Svelte-Component-Structure

**Phase:** 2  
**Priority:** Medium  
**Trigger:** Svelte files exist (*.svelte)  
**Target:** Svelte components

**Prompt:**
```
IMPORTANT - Svelte Component Structure:

When generating Svelte components, follow proper structure:

1. **Standard structure**: Every .svelte file should have:
   ```svelte
   <script>
     // JavaScript logic
   </script>

   <!-- HTML template -->

   <style>
     /* CSS styles */
   </style>
   ```

2. **Props**: Define props using `export let propName;`

3. **Reactivity**: Use `$:` for reactive statements.

4. **Events**: Use `on:event` syntax for event handling.

5. **Scoped styles**: Styles in .svelte files are scoped by default.

NOTE: Following Svelte conventions ensures proper reactivity and component behavior.
```

---

# Phase 3: Advanced Rules (Framework-Specific)

---

## Rule: NextJS-App-Router-Structure

**Phase:** 3  
**Priority:** Medium  
**Trigger:** Next.js project detected (next.config.js OR next.config.mjs exists)  
**Target:** app/ directory structure

**Prompt:**
```
IMPORTANT - Next.js App Router Structure:

When generating files for Next.js App Router (app/ directory), follow proper conventions:

1. **Page files**: Route pages must be named `page.tsx` or `page.jsx`:
   - app/page.tsx → /
   - app/about/page.tsx → /about
   - app/blog/[slug]/page.tsx → /blog/:slug

2. **Layout files**: Shared layouts must be named `layout.tsx`:
   - app/layout.tsx → Root layout (REQUIRED)
   - app/dashboard/layout.tsx → Dashboard section layout

3. **Loading states**: Use `loading.tsx` for Suspense boundaries:
   - app/dashboard/loading.tsx → Loading UI for dashboard

4. **Error handling**: Use `error.tsx` for error boundaries:
   - app/dashboard/error.tsx → Error UI for dashboard

5. **API Routes**: Use route.ts for API endpoints:
   - app/api/users/route.ts → /api/users

6. **Metadata**: Export metadata from page.tsx:
   ```tsx
   export const metadata = {
     title: 'Page Title',
     description: 'Page description'
   };
   ```

7. **Server vs Client**: Add 'use client' directive for client components:
   ```tsx
   'use client';
   // Client component code
   ```

NOTE: Incorrect naming will result in routes not being recognized by Next.js.
```

---

## Rule: NuxtJS-Directory-Structure

**Phase:** 3  
**Priority:** Medium  
**Trigger:** Nuxt.js project detected (nuxt.config.ts OR nuxt.config.js exists)  
**Target:** Nuxt directory structure

**Prompt:**
```
IMPORTANT - Nuxt.js Directory Structure:

When generating files for Nuxt.js, follow proper conventions:

1. **Pages**: Auto-routed pages in pages/ directory:
   - pages/index.vue → /
   - pages/about.vue → /about
   - pages/blog/[id].vue → /blog/:id

2. **Layouts**: Shared layouts in layouts/ directory:
   - layouts/default.vue → Default layout
   - layouts/auth.vue → Auth-specific layout

3. **Components**: Reusable components in components/ directory:
   - components/Button.vue → <Button />
   - components/ui/Card.vue → <UiCard />

4. **Composables**: Shared composables in composables/ directory:
   - composables/useAuth.ts → useAuth()

5. **Server**: API routes in server/api/ directory:
   - server/api/users.ts → /api/users

6. **Middleware**: Route middleware in middleware/ directory:
   - middleware/auth.ts

NOTE: Nuxt auto-imports from these directories; no explicit imports needed.
```

---

## Rule: Remix-Route-Structure

**Phase:** 3  
**Priority:** Medium  
**Trigger:** Remix project detected (remix.config.js exists)  
**Target:** Remix routes directory

**Prompt:**
```
IMPORTANT - Remix Route Structure:

When generating files for Remix, follow proper conventions:

1. **Routes**: File-based routing in app/routes/ directory:
   - app/routes/_index.tsx → /
   - app/routes/about.tsx → /about
   - app/routes/blog.$slug.tsx → /blog/:slug

2. **Loaders**: Data loading with loader function:
   ```tsx
   export async function loader({ params }) {
     return json({ data: await fetchData(params.id) });
   }
   ```

3. **Actions**: Form handling with action function:
   ```tsx
   export async function action({ request }) {
     const formData = await request.formData();
     // Process form
     return redirect('/success');
   }
   ```

4. **Meta**: Page metadata with meta function:
   ```tsx
   export function meta() {
     return [{ title: 'Page Title' }];
   }
   ```

5. **Layout routes**: Use _layout.tsx for nested layouts.

6. **Error boundaries**: Use ErrorBoundary export for error handling.

NOTE: Remix uses file naming conventions for routing; follow the dot notation for dynamic segments.
```

---

## Rule: Test-File-Conventions

**Phase:** 3  
**Priority:** Low  
**Trigger:** Test files exist (*.test.ts, *.spec.ts, *.test.tsx, *.spec.tsx)  
**Target:** Test file structure and imports

**Prompt:**
```
RECOMMENDED - Test File Conventions:

When generating test files, follow testing conventions:

1. **File naming**: Use consistent naming:
   - Component.test.tsx (Jest/Vitest)
   - Component.spec.tsx (Vitest/Playwright)
   - __tests__/Component.test.tsx (alternative)

2. **Test structure**: Follow AAA pattern:
   ```typescript
   describe('ComponentName', () => {
     it('should do something', () => {
       // Arrange
       const props = { title: 'Test' };
       
       // Act
       render(<Component {...props} />);
       
       // Assert
       expect(screen.getByText('Test')).toBeInTheDocument();
     });
   });
   ```

3. **Imports**: Import from testing library correctly:
   ```typescript
   import { render, screen } from '@testing-library/react';
   import userEvent from '@testing-library/user-event';
   ```

4. **Mock files**: Place mocks in __mocks__/ directory adjacent to the module.

5. **Test utilities**: Share test utilities in a test-utils file.

NOTE: Consistent test structure improves maintainability and readability.
```

---

## Rule: OpenAPI-Specification-Consistency

**Phase:** 3  
**Priority:** Low  
**Trigger:** OpenAPI/Swagger file exists (openapi.yaml, openapi.json, swagger.yaml, swagger.json)  
**Target:** API implementation files

**Prompt:**
```
RECOMMENDED - OpenAPI Specification Consistency:

When generating API implementations alongside OpenAPI specs, ensure consistency:

1. **Endpoint paths**: API routes must match paths in OpenAPI spec:
   - OpenAPI: /api/v1/users
   - Implementation: router.get('/api/v1/users', handler)

2. **HTTP methods**: Match methods exactly:
   - OpenAPI: GET /users, POST /users
   - Implementation: router.get('/users'), router.post('/users')

3. **Request/Response schemas**: Match defined schemas:
   - OpenAPI defines UserRequest schema
   - Implementation validates against UserRequest

4. **Status codes**: Return specified status codes:
   - OpenAPI: 201 for created, 404 for not found
   - Implementation: res.status(201), res.status(404)

5. **Error responses**: Match error response format from spec.

NOTE: Divergence between spec and implementation causes integration issues.
```

---

## Rule: Flask-Blueprint-Structure

**Phase:** 3  
**Priority:** Low  
**Trigger:** Flask Blueprints detected (from flask import Blueprint)  
**Target:** Blueprint registration in main app

**Prompt:**
```
RECOMMENDED - Flask Blueprint Structure:

When using Flask Blueprints, ensure proper structure and registration:

1. **Blueprint creation**: Create blueprints in separate files:
   ```python
   # routes/users.py
   from flask import Blueprint
   
   users_bp = Blueprint('users', __name__)
   
   @users_bp.route('/users')
   def get_users():
       return jsonify([])
   ```

2. **Blueprint registration**: Register blueprints in main app:
   ```python
   # app.py
   from routes.users import users_bp
   
   app.register_blueprint(users_bp, url_prefix='/api')
   ```

3. **URL prefix**: Use url_prefix for namespacing:
   ```python
   app.register_blueprint(api_bp, url_prefix='/api/v1')
   ```

4. **Blueprint organization**: Group related routes into blueprints:
   - routes/auth.py - Authentication routes
   - routes/users.py - User management routes
   - routes/posts.py - Post management routes

5. **Template folders**: Blueprints can have their own template folders:
   ```python
   users_bp = Blueprint('users', __name__, template_folder='templates')
   ```

NOTE: Blueprints help organize large Flask applications.
```

---

## Rule: FastAPI-Router-Structure

**Phase:** 3  
**Priority:** Low  
**Trigger:** FastAPI detected (from fastapi import FastAPI)  
**Target:** APIRouter usage and registration

**Prompt:**
```
RECOMMENDED - FastAPI Router Structure:

When using FastAPI with routers, ensure proper structure:

1. **Router creation**: Create routers in separate files:
   ```python
   # routers/users.py
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/users")
   async def get_users():
       return []
   ```

2. **Router registration**: Include routers in main app:
   ```python
   # main.py
   from fastapi import FastAPI
   from routers import users
   
   app = FastAPI()
   app.include_router(users.router, prefix="/api/v1", tags=["users"])
   ```

3. **Tags and prefixes**: Use tags for API documentation grouping and prefixes for URL namespacing.

4. **Dependencies**: Define route dependencies at router level:
   ```python
   router = APIRouter(dependencies=[Depends(get_current_user)])
   ```

5. **Response models**: Always define response models with Pydantic:
   ```python
   @router.get("/users", response_model=List[UserResponse])
   async def get_users():
       return []
   ```

NOTE: Proper router structure improves API organization and documentation.
```

---

## Rule: Common-Pitfall-Calculator-Eval-Prevention

**Phase:** 3  
**Priority:** Low  
**Trigger:** Calculator pattern detected  
**Target:** JavaScript implementation

**Prompt:**
```
CRITICAL - Calculator Implementation Pitfall Prevention:

When implementing calculator logic, AVOID these common pitfalls:

1. **NEVER use eval()**: eval() is a security risk and should NEVER be used for calculation.
   ❌ BAD: const result = eval(expression);
   ✅ GOOD: Implement proper expression parsing

2. **Avoid complex state management**: Keep state simple (current value, operator, previous value).
   ❌ BAD: tokens array with complex manipulation
   ✅ GOOD: Simple variables for current, previous, operator

3. **Proper error handling**: Handle division by zero and invalid operations:
   ```javascript
   if (operator === '/' && num2 === 0) {
     return 'Error';
   }
   ```

4. **Input validation**: Validate all inputs before processing:
   - Prevent multiple decimal points
   - Prevent leading zeros (except "0.")
   - Handle negative numbers properly

5. **Clear error states**: Use proper error state management, not string-based ("Error", "Error1", etc.)

REMEMBER: Simplicity is better than cleverness. A 150-line simple calculator is better than a 350-line complex one.
```

---

## Rule: Dockerfile-Docker-Compose-Service-Consistency

**Phase:** 3  
**Priority:** Low  
**Trigger:** Dockerfile exists  
**Target:** docker-compose.yml exists

**Prompt:**
```
RECOMMENDED - Dockerfile and Docker Compose Consistency:

When generating both Dockerfile and docker-compose.yml, ensure service consistency:

1. **Build context**: If docker-compose.yml references Dockerfile (e.g., build: .), ensure Dockerfile exists in that directory.

2. **Service names**: Service names in docker-compose.yml should be meaningful and consistent with the project structure.

3. **Port mappings**: Ensure ports exposed in Dockerfile (EXPOSE 3000) match ports in docker-compose.yml (ports: "3000:3000").

4. **Volume mounts**: If docker-compose.yml mounts volumes, ensure the corresponding directories/files exist or will be created.

5. **Environment variables**: If Dockerfile uses ENV variables, ensure they are either set in Dockerfile or docker-compose.yml environment section.

NOTE: This rule helps prevent container startup failures.
```

---

## Rule: Node-Package-Scripts-File-Consistency

**Phase:** 3  
**Priority:** Low  
**Trigger:** package.json with scripts exists  
**Target:** Files referenced in scripts exist

**Prompt:**
```
RECOMMENDED - Node.js Package Scripts Consistency:

When defining scripts in package.json, ensure referenced files exist:

1. **Start script**: If "start": "node server.js", ensure server.js exists.

2. **Test script**: If "test": "jest", ensure jest configuration exists (jest.config.js or in package.json).

3. **Build script**: If "build": "webpack", ensure webpack.config.js exists.

4. **Dev script**: If "dev": "nodemon src/index.js", ensure src/index.js exists.

5. **Common scripts to verify**:
   ```json
   {
     "scripts": {
       "start": "node server.js",    // Verify server.js
       "dev": "nodemon app.js",       // Verify app.js
       "test": "jest",                // Verify test files
       "build": "webpack"             // Verify webpack config
     }
   }
   ```

NOTE: Missing script dependencies will cause npm run commands to fail.
```

---

# Phase 4: Runtime Constraints (Critical - Syntax Check Bypass)

These rules address errors that pass syntax checking but fail at runtime.
**New in v2.3:** Runtime constraint rules for Python/Flask/SQLAlchemy

---

## Rule: SQLAlchemy-Reserved-Attribute-Names

**Phase:** 4  
**Priority:** Critical  
**Trigger:** SQLAlchemy models detected (from sqlalchemy import, db.Model, Base)  
**Target:** Model class definitions with Column attributes

**Prompt:**
```
CRITICAL - SQLAlchemy Reserved Attribute Names:

When defining SQLAlchemy ORM models, NEVER use these reserved attribute names as column names:

1. **FORBIDDEN attribute names** (will cause InvalidRequestError at runtime):
   - `metadata` - Reserved for MetaData instance in declarative base
   - `registry` - Reserved for mapper registry
   - `query` - Reserved for Model.query interface (Flask-SQLAlchemy)

2. **Correct naming alternatives**:
   ❌ BAD:  metadata = Column(JSON, nullable=True)
   ✅ GOOD: item_metadata = Column(JSON, nullable=True)
   ✅ GOOD: meta_data = Column(JSON, nullable=True)
   ✅ GOOD: extra_data = Column(JSON, nullable=True)

3. **Python reserved keywords** also cannot be used as attribute names:
   - `from`, `import`, `class`, `def`, `return`, `if`, `else`, `for`, `while`, `try`, `except`, `with`, `as`, `global`, `lambda`, `yield`, `raise`, `pass`, `break`, `continue`, `and`, `or`, `not`, `in`, `is`, `None`, `True`, `False`
   
   If you need a column named after a keyword, use trailing underscore:
   ❌ BAD:  from = Column(String(255))
   ✅ GOOD: from_ = Column(String(255))  # with 'from' as actual DB column name via Column('from', ...)

4. **Error you'll see if violated**:
   sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved for the MetaData instance when using a declarative base class.

VERIFY: Before completing model generation, scan all Column() definitions for forbidden attribute names.
```

---

## Rule: Python-Circular-Import-Prevention

**Phase:** 4  
**Priority:** Critical  
**Trigger:** Flask or Django application structure detected  
**Target:** Multiple Python files with inter-module imports

**Prompt:**
```
CRITICAL - Circular Import Prevention:

Circular imports cause ImportError at runtime even though each file passes syntax check individually.

1. **Common circular import patterns to AVOID**:
   
   ❌ BAD Pattern (models.py ↔ routes.py circular):
   ```python
   # models.py
   from routes import some_function  # imports routes
   
   # routes.py
   from models import User  # imports models → circular!
   ```

2. **Flask-SQLAlchemy safe pattern**:
   ```python
   # extensions.py (create separate file for extensions)
   from flask_sqlalchemy import SQLAlchemy
   db = SQLAlchemy()
   
   # models.py
   from extensions import db  # import db from extensions
   class User(db.Model): ...
   
   # routes.py
   from extensions import db
   from models import User  # safe - models doesn't import routes
   ```

3. **Application Factory Pattern** (recommended for Flask):
   ```python
   # app/__init__.py
   def create_app():
       app = Flask(__name__)
       from .routes import main_bp  # import INSIDE function
       app.register_blueprint(main_bp)
       return app
   ```

4. **NEVER name your file same as a module you import**:
   ❌ BAD: flask.py, requests.py, json.py, os.py
   ✅ GOOD: app.py, main.py, server.py, utils.py

5. **Error you'll see if violated**:
   ImportError: cannot import name 'X' from partially initialized module 'Y' (most likely due to a circular import)

VERIFY: Ensure models.py does NOT import from routes/views, and routes/views import FROM models (one-way dependency).
```

---

## Rule: Flask-Application-Context-Required

**Phase:** 4  
**Priority:** High  
**Trigger:** Flask-SQLAlchemy detected (from flask_sqlalchemy import SQLAlchemy)  
**Target:** Database initialization and model operations

**Prompt:**
```
CRITICAL - Flask Application Context Required:

Flask-SQLAlchemy operations require an active application context. This is NOT detected by syntax check.

1. **db.create_all() requires app context**:
   ❌ BAD (will fail at runtime):
   ```python
   app = Flask(__name__)
   db = SQLAlchemy(app)
   db.create_all()  # RuntimeError: Working outside of application context
   ```
   
   ✅ GOOD:
   ```python
   app = Flask(__name__)
   db = SQLAlchemy(app)
   with app.app_context():
       db.create_all()
   ```

2. **Correct initialization in main.py**:
   ```python
   def create_app():
       app = Flask(__name__)
       db.init_app(app)
       
       with app.app_context():
           db.create_all()
       
       return app
   
   if __name__ == '__main__':
       app = create_app()
       app.run()
   ```

3. **Correct initialization in database.py**:
   ```python
   def init_db(app):
       db.init_app(app)
       with app.app_context():
           db.create_all()
   ```

4. **Error you'll see if violated**:
   RuntimeError: Working outside of application context.

VERIFY: Every db.create_all() call must be inside `with app.app_context():` block.
```

---

## Rule: Cross-Platform-Package-Compatibility

**Phase:** 4  
**Priority:** Critical  
**Trigger:** requirements.txt generation  
**Target:** Package list for pip install

**Prompt:**
```
CRITICAL - Cross-Platform Package Compatibility:

Some packages require C compilation and will FAIL pip install on systems without build tools.

1. **AVOID these packages in requirements.txt** (require C compilation):
   - `psycopg2` - Requires PostgreSQL headers and C compiler
   - `psycopg2-binary` - May lack wheels for newer Python versions (3.12+, 3.13+)
   - `gevent` - Requires C compiler for libev/libuv
   - `uvloop` - Unix-only, requires C compiler
   - `mysqlclient` - Requires MySQL headers and C compiler
   - `greenlet` (old versions) - May require compilation

2. **Safe alternatives**:
   | Avoid | Use Instead |
   |-------|-------------|
   | psycopg2, psycopg2-binary | SQLite (default) or pg8000 (pure Python) |
   | gevent | eventlet or threading (async_mode='threading') |
   | uvloop | Default asyncio event loop |
   | mysqlclient | pymysql (pure Python) |

3. **SQLite is the safest default** for development:
   - No additional packages needed
   - Works on all platforms without compilation
   - config.py: SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'

4. **If PostgreSQL is required**, add note in README:
   ```
   # PostgreSQL users must install:
   # - PostgreSQL server
   # - pg_config (usually in postgresql-devel or libpq-dev package)
   # Then: pip install psycopg2-binary
   ```

5. **Error you'll see if violated**:
   - "pg_config executable not found"
   - "error: command 'gcc' failed"
   - "Microsoft Visual C++ 14.0 or greater is required"

VERIFY: requirements.txt should work with just `pip install -r requirements.txt` on a fresh Windows/Mac/Linux system without any C compiler.
```

---

## Rule: SQLAlchemy-Relationship-Consistency

**Phase:** 4  
**Priority:** High  
**Trigger:** SQLAlchemy relationships detected (relationship(), ForeignKey)  
**Target:** Model class definitions with relationships

**Prompt:**
```
IMPORTANT - SQLAlchemy Relationship Consistency:

Relationship definitions must be consistent between related models, or runtime errors occur.

1. **back_populates must match exactly**:
   ❌ BAD (will fail at runtime):
   ```python
   class User(Base):
       posts = relationship('Post', back_populates='author')
   
   class Post(Base):
       user = relationship('User', back_populates='posts')  # 'user' != 'author'
   ```
   
   ✅ GOOD:
   ```python
   class User(Base):
       posts = relationship('Post', back_populates='author')
   
   class Post(Base):
       author = relationship('User', back_populates='posts')  # matches!
   ```

2. **ForeignKey must reference existing column**:
   ```python
   class Post(Base):
       user_id = Column(Integer, ForeignKey('users.id'))  # 'users' = __tablename__ of User
       author = relationship('User', back_populates='posts')
   ```

3. **Cascade rules for one-to-many**:
   - delete-orphan cascade goes on the "one" side only
   ```python
   class User(Base):
       posts = relationship('Post', back_populates='author', cascade='all, delete-orphan')
   ```

4. **Error you'll see if violated**:
   - "Could not locate the relationship 'X' in mapper 'Y'"
   - "Relationship 'X' expects 'Y' but got 'Z'"

VERIFY: For every back_populates='X', ensure the other model has an attribute named exactly 'X'.
```

---

# End of Enhanced Rules v2.3

**Total Rules:** 24  
**Phase 1 (High Priority):** 4 rules  
**Phase 2 (Medium Priority):** 5 rules  
**Phase 3 (Low/Medium Priority):** 10 rules  
**Phase 4 (Runtime Constraints - Critical):** 5 rules

**New in v2.3:**
- SQLAlchemy Reserved Attribute Names (metadata, registry, query)
- Python Circular Import Prevention
- Flask Application Context Required
- Cross-Platform Package Compatibility
- SQLAlchemy Relationship Consistency

**Previous versions:**
- v2.2: Next.js App Router patterns, Nuxt.js/Remix patterns, Test file conventions
- v2.1: Professional UI: No Emojis policy
- v2.0: Flask/FastAPI/Express patterns, Vue.js/Svelte component structure, Calculator pitfall prevention

---

## Cross-Reference with app_patterns.json

This file works in conjunction with app_patterns.json:

| app_patterns.json Pattern | Related Rules in This File |
|---------------------------|---------------------------|
| calculator | HTML-CSS-Reference, HTML-JavaScript-Reference, Calculator-Eval-Prevention |
| todo | HTML-CSS-Reference, HTML-JavaScript-Reference, Professional-UI-No-Emojis |
| dashboard | HTML-CSS-Reference, HTML-JavaScript-Reference |
| login | HTML-CSS-Reference, HTML-JavaScript-Reference, Professional-UI-No-Emojis |
| All React patterns | React-Component-CSS-Import |
| All Vue patterns | Vue-Component-Structure |

---

## Cross-Reference with ui-knowledge.json

This file works in conjunction with ui-knowledge.json:

| ui-knowledge.json Section | Related Rules |
|---------------------------|---------------|
| components.button | Accessibility requirements in all UI rules |
| components.input | Form validation in contact_form pattern |
| components.modal | Professional-UI-No-Emojis, accessibility |
| ux_laws.jakobs_law | All framework-specific conventions |
| ux_laws.cognitive_load | Simple implementation preferences |

---

## Usage Notes

1. **Automatic Application**: These rules are automatically applied based on detected file patterns during code generation.

2. **Override Mechanism**: Create a project-specific `.cognix/file_reference_rules.md` to override or extend these rules.

3. **Disable Rules**: To disable a rule in your project, create an empty rule with the same name in your project-specific rules file.

4. **Custom Rules**: You can add custom rules following the same format in your project-specific rules file.

---

**END OF DEFAULT_FILE_REFERENCE_RULES_V2.2.MD**