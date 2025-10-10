# Fix Guide for Remaining Cogs

## Status
- ✅ **Fixed and Working (7 cogs)**: economy, utility, admin, fun, tickets, events, moderation
- ⚠️ **Needs Fixing (8 cogs)**: couples, reminders, automod, levels, announcements, audit, activity_log, developer

## Root Cause of "Unknown cmd_id received" Error

The error occurs when:
1. Cogs fail to load due to import errors or syntax errors
2. Commands aren't registered in Discord because the cog didn't load
3. User tries to use a command, but Discord sends an interaction for a cmd_id the bot doesn't recognize

## What Was Fixed

### economy.py ✅
- Removed `@app_commands.default_permissions` from class
- Converted all `app_commands.Range` to `@interactions.slash_option` with `min_value`/`max_value`
- Converted `discord.Role` to `interactions.Role`
- Removed problematic lifecycle methods (`cog_load`, `drop`)
- Converted `app_commands.Group` to subcommands with `sub_cmd_name`

### utility.py ✅
- Fixed `drop()` method to use `asyncio.create_task()`
- Created `format_dt()` helper to replace `discord.utils.format_dt`
- Converted all `@app_commands.describe` to `@interactions.slash_option`
- Converted all `@app_commands.choices` to `choices` parameter in slash_option
- Fixed autocomplete functions to use `interactions.AutocompleteContext`
- Replaced all discord type references with interactions types

### moderation.py ✅
- Removed `@app_commands.default_permissions` from class
- Converted `app_commands.Range` parameters to `@interactions.slash_option`

## Required Fixes for Remaining Cogs

### Pattern 1: @app_commands.choices decorator

**OLD:**
```python
@app_commands.choices(rule_type=[
    app_commands.Choice(name="Filter", value="filter"),
])
async def command(self, ctx, rule_type: app_commands.Choice[str]):
    value = rule_type.value
```

**NEW:**
```python
@interactions.slash_option(
    name="rule_type",
    description="Type of rule",
    opt_type=interactions.OptionType.STRING,
    required=True,
    choices=[
        interactions.SlashCommandChoice(name="Filter", value="filter"),
    ],
)
async def command(self, ctx, rule_type: str):
    value = rule_type  # Now it's directly a string
```

### Pattern 2: @app_commands.describe decorator

**OLD:**
```python
@app_commands.describe(
    param="Description here",
)
async def command(self, ctx, param: str):
```

**NEW:**
```python
@interactions.slash_option(
    name="param",
    description="Description here",
    opt_type=interactions.OptionType.STRING,
    required=True,
)
async def command(self, ctx, param: str):
```

### Pattern 3: app_commands.Range parameters

**OLD:**
```python
async def command(self, ctx, num: app_commands.Range[int, 1, 100]):
```

**NEW:**
```python
@interactions.slash_option(
    name="num",
    description="Number between 1-100",
    opt_type=interactions.OptionType.INTEGER,
    min_value=1,
    max_value=100,
    required=True,
)
async def command(self, ctx, num: int):
```

### Pattern 4: Default permissions on class

**OLD:**
```python
@app_commands.default_permissions(manage_guild=True)
class MyCog(interactions.Extension):
```

**NEW:**
```python
class MyCog(interactions.Extension):
    # Add to each command:
    @interactions.slash_command(
        name="command",
        description="...",
        default_member_permissions=interactions.Permissions.MANAGE_GUILD,
    )
```

### Pattern 5: Lifecycle methods

**OLD:**
```python
async def cog_load(self) -> None:
    # initialization code

def drop(self) -> None:
    await self.cleanup()  # ERROR: await in non-async function
```

**NEW:**
```python
# In __init__ for synchronous setup
def __init__(self, bot):
    self.bot = bot
    # sync init only

# For async cleanup:
def drop(self) -> None:
    import asyncio
    asyncio.create_task(self.cleanup())
```

## Specific Fixes Needed

### automod.py
- Line 53: Remove `@app_commands.choices`, add choices to `@interactions.slash_option`
- Line 54: Change parameter type from `app_commands.Choice[str]` to `str`
- Line 74-76: Convert `@app_commands.describe` to `@interactions.slash_option`
- Line 106: Convert `app_commands.Range` to slash_option with min/max_value
- Line 126-134: Convert describe/Range to slash_option

### levels.py
- Check for `@app_commands` decorators
- Convert any Range parameters
- Add slash_option decorators for all parameters

### announcements.py
- Check for `@app_commands` decorators
- Remove any async cog_load methods or fix them
- Convert parameters to slash_option decorators

### audit.py
- Similar fixes as above
- GroupCog commands need to use `sub_cmd_name` parameter

### couples.py
- Line 198: Has an `app_commands` reference at module level
- Convert all command decorators

### reminders.py
- Line 18: Has `async def cog_load()` - this is fine in interactions.py
- Check for other app_commands references

### developer.py
- Line 13: Has `app_commands` reference
- Convert all command decorators

### activity_log.py
- Most complex: depends on `bot/services/activity_logger.py`
- `activity_logger.py` imports discord directly (line 7-9)
- Need to convert activity_logger.py to use interactions types
- 67 discord references in activity_logger.py need conversion

## Quick Fix Script

For bulk conversion, you can use sed:

```bash
# Remove @app_commands.choices decorator lines (will need manual recreation)
sed -i '/@app_commands\.choices/d' bot/cogs/*.py

# Remove @app_commands.describe decorator lines (will need manual recreation)  
sed -i '/@app_commands\.describe/d' bot/cogs/*.py
```

**WARNING**: This will remove the decorators but you'll need to manually add the equivalent `@interactions.slash_option` decorators!

## Testing After Fixes

```bash
# Test if all cogs can be imported
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

cogs = ['economy', 'utility', 'admin', 'fun', 'tickets', 'events', 'moderation',
        'couples', 'reminders', 'automod', 'levels', 'announcements', 'audit', 
        'activity_log', 'developer']

for cog in cogs:
    try:
        exec(f'from bot.cogs import {cog}')
        print(f'✓ {cog}')
    except Exception as e:
        print(f'✗ {cog}: {e}')
EOF
```

## Priority Order

1. **HIGH**: automod, levels, announcements, audit (have simple @app_commands fixes)
2. **MEDIUM**: couples, reminders, developer (have module-level issues)
3. **LOW**: activity_log (requires fixing activity_logger.py service - 67 references)

## Expected Outcome

Once all cogs are fixed:
- All 15 cogs will load successfully
- All slash commands will be properly registered with Discord
- "Unknown cmd_id received" error will be resolved
- Bot will respond to all commands correctly
