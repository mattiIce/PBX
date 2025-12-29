# Auto Attendant Submenu Feature Implementation Plan

## Overview
This document outlines the implementation plan for adding hierarchical submenu support to the PBX auto-attendant system.

## Feature Request
**Requested by:** @mattiIce  
**Date:** 2025-12-29  
**Related PR:** #[PR_NUMBER] (Textarea size increase)

### User Story
As a PBX administrator, I want to create multi-level menus in the auto-attendant so that:
- Callers can navigate through nested menu options
- Complex organizational structures can be represented
- Related departments can be grouped under parent menu items

### Example Use Case
```
Main Menu:
├── Press 1: Sales
├── Press 2: Support
├── Press 3: Directions and Shipping/Receiving (SUBMENU)
│   ├── Press 1: Directions
│   └── Press 2: Shipping and Receiving → Extension [configurable]
└── Press 0: Operator
```

When a caller presses 3, instead of routing to an extension, they hear a submenu prompt with additional options.

## Current Implementation Analysis

### Database Schema (Current)
The current auto-attendant uses two tables:

**auto_attendant_config:**
- id (PRIMARY KEY)
- enabled (BOOLEAN)
- extension (TEXT)
- timeout (INTEGER)
- max_retries (INTEGER)
- audio_path (TEXT)
- updated_at (TIMESTAMP)

**auto_attendant_menu_options:**
- digit (PRIMARY KEY)
- destination (TEXT) - Currently only supports extension numbers
- description (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

### Current Limitations
1. Single-level menu structure only
2. `destination` field is a simple string (extension number)
3. No concept of parent-child relationships
4. No menu hierarchy tracking
5. State machine (`AAState` enum) doesn't support submenu states

## Proposed Implementation

### 1. Database Schema Changes

#### Option A: Extend Existing Table
Add columns to `auto_attendant_menu_options`:
```sql
ALTER TABLE auto_attendant_menu_options ADD COLUMN menu_id TEXT DEFAULT 'main';
ALTER TABLE auto_attendant_menu_options ADD COLUMN destination_type TEXT DEFAULT 'extension';
ALTER TABLE auto_attendant_menu_options ADD COLUMN parent_menu TEXT DEFAULT NULL;
```

**Fields:**
- `menu_id`: Unique identifier for this menu level (e.g., 'main', 'shipping', 'sales-submenu')
- `destination_type`: 'extension' | 'submenu' | 'queue' | 'voicemail'
- `parent_menu`: References the menu_id of the parent menu (NULL for main menu)

#### Option B: Create Separate Tables
```sql
-- Menu structure table
CREATE TABLE auto_attendant_menus (
    menu_id TEXT PRIMARY KEY,
    parent_menu_id TEXT,
    menu_name TEXT,
    prompt_text TEXT,
    timeout INTEGER DEFAULT 10,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_menu_id) REFERENCES auto_attendant_menus(menu_id)
);

-- Menu options linking table
CREATE TABLE auto_attendant_menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_id TEXT NOT NULL,
    digit TEXT NOT NULL,
    destination_type TEXT NOT NULL,
    destination_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (menu_id) REFERENCES auto_attendant_menus(menu_id),
    UNIQUE(menu_id, digit)
);
```

**Recommendation:** Option B is cleaner and more scalable for complex menu hierarchies.

### 2. Backend Changes

#### AutoAttendant Class (`pbx/features/auto_attendant.py`)

**New Enums:**
```python
class DestinationType(Enum):
    EXTENSION = "extension"
    SUBMENU = "submenu"
    QUEUE = "queue"
    VOICEMAIL = "voicemail"
    OPERATOR = "operator"

class AAState(Enum):
    WELCOME = "welcome"
    MAIN_MENU = "main_menu"
    SUBMENU = "submenu"  # NEW
    TRANSFERRING = "transferring"
    INVALID = "invalid"
    TIMEOUT = "timeout"
    ENDED = "ended"
```

**New Methods:**
```python
def _init_menus_database(self):
    """Initialize new menu structure tables"""
    
def _load_menu_structure(self, menu_id='main'):
    """Load menu options for a specific menu level"""
    
def _get_submenu_by_id(self, menu_id):
    """Retrieve submenu configuration"""
    
def create_submenu(self, menu_id, parent_menu_id, menu_name, prompt_text):
    """Create a new submenu"""
    
def add_menu_item(self, menu_id, digit, destination_type, destination_value, description):
    """Add item to a specific menu (main or submenu)"""
    
def navigate_to_submenu(self, call_id, menu_id):
    """Navigate call session to a submenu"""
    
def navigate_back_to_parent(self, call_id):
    """Return to parent menu (if applicable)"""
```

**Session Management:**
- Track current menu level in call session
- Maintain menu navigation history stack
- Support "go back" functionality (press * or 9)

#### API Changes (`pbx/api/rest_api.py`)

**New Endpoints:**
```
GET    /api/auto-attendant/menus                    # List all menus
GET    /api/auto-attendant/menus/{menu_id}          # Get specific menu
POST   /api/auto-attendant/menus                    # Create new menu
PUT    /api/auto-attendant/menus/{menu_id}          # Update menu
DELETE /api/auto-attendant/menus/{menu_id}          # Delete menu

GET    /api/auto-attendant/menus/{menu_id}/items    # Get menu items
POST   /api/auto-attendant/menus/{menu_id}/items    # Add menu item
PUT    /api/auto-attendant/menus/{menu_id}/items/{digit}  # Update item
DELETE /api/auto-attendant/menus/{menu_id}/items/{digit}  # Delete item

GET    /api/auto-attendant/menu-tree                # Get complete menu hierarchy
```

**Request/Response Schemas:**
```json
// Create Menu
POST /api/auto-attendant/menus
{
  "menu_id": "shipping-submenu",
  "parent_menu_id": "main",
  "menu_name": "Shipping and Receiving",
  "prompt_text": "For directions, press 1. For shipping and receiving, press 2."
}

// Add Menu Item
POST /api/auto-attendant/menus/shipping-submenu/items
{
  "digit": "2",
  "destination_type": "extension",
  "destination_value": "105",
  "description": "Shipping and Receiving"
}

// Menu Tree Response
GET /api/auto-attendant/menu-tree
{
  "menu_id": "main",
  "menu_name": "Main Menu",
  "items": [
    {
      "digit": "1",
      "destination_type": "extension",
      "destination_value": "100",
      "description": "Sales"
    },
    {
      "digit": "3",
      "destination_type": "submenu",
      "destination_value": "shipping-submenu",
      "description": "Directions and Shipping",
      "submenu": {
        "menu_id": "shipping-submenu",
        "menu_name": "Shipping and Receiving",
        "items": [...]
      }
    }
  ]
}
```

### 3. Frontend Changes (`admin/index.html`, `admin/js/auto_attendant.js`)

#### UI Components Needed:

1. **Menu Tree Visualization**
   - Hierarchical tree view showing menu structure
   - Drag-and-drop support for reorganizing
   - Expand/collapse submenu nodes

2. **Menu Item Editor**
   - Destination type selector (Extension/Submenu/Queue)
   - Conditional fields based on type
   - If type = "Submenu": Show submenu selector or "Create New" option

3. **Submenu Creator Modal**
   - Menu name input
   - Parent menu selector
   - Prompt text textarea (similar to main prompts)
   - Voice regeneration option

4. **Enhanced Menu Options Table**
   - Show destination type icon/badge
   - Submenu indicators
   - Navigation to edit submenu
   - Parent menu breadcrumb

#### JavaScript Functions:
```javascript
// Load menu tree
async function loadMenuTree()

// Create submenu
async function createSubmenu(parentMenuId, menuData)

// Edit menu item with type selection
function showEditMenuItemModal(menuId, digit, item)

// Navigate to submenu editing
function navigateToSubmenu(menuId)

// Breadcrumb navigation
function renderMenuBreadcrumb(currentMenuId)
```

### 4. Voice Prompt Generation

**New Prompts Required:**
- Submenu prompts (one per submenu)
- "Going back to previous menu" prompt
- "Invalid submenu option" prompt

**Prompt Template Handling:**
- Support for {menu_name} placeholder
- Support for {parent_menu} placeholder
- Dynamic prompt generation per submenu

### 5. Call Flow Logic

**Updated Call Handling:**
```
1. Call arrives at auto-attendant
2. Play welcome prompt
3. Enter menu state (initially 'main')
4. Collect DTMF digit
5. Look up digit in current menu context
6. If destination_type == 'submenu':
   - Push current menu to navigation stack
   - Load submenu
   - Play submenu prompt
   - Return to step 4
7. If destination_type == 'extension':
   - Transfer to extension
8. Special digits:
   - * or 9: Go back to parent menu (if in submenu)
   - 0: Transfer to operator
   - #: Repeat current menu
```

## Migration Strategy

### Phase 1: Database Migration
1. Create new tables (if using Option B)
2. Migrate existing menu_options to new structure
3. Set all existing items to menu_id='main', destination_type='extension'
4. Test data integrity

### Phase 2: Backend Implementation
1. Update AutoAttendant class with new methods
2. Implement backward compatibility layer
3. Add API endpoints
4. Write unit tests for submenu logic

### Phase 3: Frontend Implementation
1. Update UI to show menu tree
2. Add submenu creation/editing
3. Update menu item form with type selector
4. Add breadcrumb navigation

### Phase 4: Testing & Documentation
1. Integration testing
2. UI/UX testing
3. Update user documentation
4. Create migration guide for existing deployments

## Backward Compatibility

**Requirements:**
- Existing single-level menus must continue to work
- No breaking changes to current API endpoints
- Config file format remains compatible
- Database migration is automatic and reversible

**Strategy:**
- Treat all existing configurations as 'main' menu
- Default destination_type to 'extension' for legacy data
- Maintain existing API endpoints alongside new ones
- Version API responses to support both formats

## Testing Checklist

- [ ] Create submenu via API
- [ ] Edit submenu via UI
- [ ] Delete submenu with cascade handling
- [ ] Navigate through multiple menu levels
- [ ] Test "go back" functionality
- [ ] Test timeout handling in submenus
- [ ] Test invalid input in submenus
- [ ] Verify voice prompt generation for submenus
- [ ] Test database migration with existing data
- [ ] Performance test with deeply nested menus (5+ levels)
- [ ] Edge case: Circular menu references prevention
- [ ] Edge case: Orphaned submenu handling

## Security Considerations

1. **Input Validation:**
   - Validate menu_id uniqueness
   - Prevent circular menu references
   - Limit menu depth (max 5 levels recommended)

2. **Authorization:**
   - Only admin users can create/modify menus
   - API endpoints require authentication
   - Audit log for menu changes

3. **Data Integrity:**
   - Foreign key constraints
   - Cascade delete handling for orphaned items
   - Transaction support for complex operations

## Performance Considerations

1. **Database Queries:**
   - Index on menu_id and parent_menu_id
   - Cache menu tree structure
   - Lazy loading for submenu options

2. **Call Processing:**
   - Minimal latency for menu transitions
   - Pre-load submenu audio files
   - Efficient DTMF processing

## Documentation Updates Required

- [ ] API documentation for new endpoints
- [ ] User guide: Creating and managing submenus
- [ ] Admin guide: Best practices for menu design
- [ ] Developer guide: Menu structure and navigation
- [ ] Database schema documentation
- [ ] Migration guide from single-level to hierarchical menus

## Estimated Effort

- Database schema design: 4 hours
- Backend implementation: 16-20 hours
- API development: 12-16 hours
- Frontend UI development: 20-24 hours
- Testing: 12-16 hours
- Documentation: 8 hours

**Total: 72-88 hours (9-11 developer days)**

## Implementation Priority

**High Priority:**
1. Database schema design and migration
2. Backend submenu logic
3. Basic UI for creating submenus
4. API endpoints

**Medium Priority:**
5. Enhanced UI with tree visualization
6. Voice prompt generation for submenus
7. Breadcrumb navigation
8. Go back functionality

**Low Priority:**
9. Drag-and-drop menu reorganization
10. Advanced features (menu templates, copying)

## References

- Current implementation: `pbx/features/auto_attendant.py`
- API handlers: `pbx/api/rest_api.py`
- Frontend code: `admin/js/auto_attendant.js`
- Database: SQLite schema in auto_attendant.py `_init_database()`

## Notes

- This feature significantly enhances the auto-attendant capabilities
- Consider using this as foundation for future IVR enhancements
- May want to add visual menu designer in future iteration
- Consider integration with call queuing for advanced routing

---

**Status:** Planning Phase  
**Next Step:** Create new PR and begin implementation after current PR is merged  
**Last Updated:** 2025-12-29
