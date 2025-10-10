# Migration Status: discord.py to interactions.py

## Overview
This document tracks the migration of the ForUS Discord Bot from discord.py to interactions.py framework.

## Completed Work

### Phase 1: Core Infrastructure
- ✅ Updated `requirements.txt` to use interactions.py 5.15.0
- ✅ Migrated `bot/main.py` ForUS class from `commands.Bot` to `interactions.Client`
- ✅ Updated intents configuration
- ✅ Removed manual command syncing (interactions.py handles this automatically)
- ✅ Updated event listeners to use `@interactions.listen()` decorator

### Phase 2: Cog Migrations (Automated)
All 16 cog files have been processed with automated migration script:
- ✅ bot/cogs/fun.py (manually completed)
- ✅ bot/cogs/admin.py (manually completed)
- ⚠️ bot/cogs/economy.py (automated, needs manual review)
- ⚠️ bot/cogs/automod.py (automated, needs manual review)
- ⚠️ bot/cogs/announcements.py (automated, needs manual review)
- ⚠️ bot/cogs/moderation.py (automated, needs manual review)
- ⚠️ bot/cogs/couples.py (automated, needs manual review)
- ⚠️ bot/cogs/levels.py (automated, needs manual review)
- ⚠️ bot/cogs/audit.py (automated, needs manual review)
- ⚠️ bot/cogs/activity_log.py (automated, needs manual review)
- ⚠️ bot/cogs/events.py (automated, needs manual review)
- ⚠️ bot/cogs/utility.py (automated, needs manual review)
- ⚠️ bot/cogs/developer.py (automated, needs manual review)
- ⚠️ bot/cogs/reminders.py (automated, needs manual review)
- ⚠️ bot/cogs/tickets.py (automated, needs manual review)

## Remaining Work

### Critical Items

#### 1. Fix Syntax Errors in Automated Migrations
Each auto-migrated cog needs manual review to fix:
- Setup functions (async vs sync)
- Event listener decorators
- GroupCog patterns (need to use group_name/sub_cmd_name params)
- Permission decorators
- Autocomplete decorators
- Choice decorators for options
- Range types for integer options
- Drop methods (replacesCog unload)

#### 2. Update Services Layer
Files that need migration:
- `bot/services/presence.py` - uses discord.py Activity/Status types
- `bot/services/activity_logger.py` - may use discord types
- Any other services using discord.py types

#### 3. Update Event Handlers (bot/cogs/events.py)
- Convert `@commands.Cog.listener()` to `@interactions.listen()`
- Update event parameter types (e.g., `discord.Message` -> `interactions.Message`)
- Update event names to interactions.py event system

#### 4. Fix Common Patterns

##### Command Decorators
```python
# OLD (discord.py)
@app_commands.command(name="test", description="Test command")
async def test(self, interaction: discord.Interaction, param: str) -> None:
    await interaction.response.send_message("Hello")

# NEW (interactions.py)
@interactions.slash_command(name="test", description="Test command")
@interactions.slash_option(
    name="param",
    description="Parameter description",
    opt_type=interactions.OptionType.STRING,
    required=True,
)
async def test(self, ctx: interactions.SlashContext, param: str) -> None:
    await ctx.send("Hello")
```

##### Command Groups
```python
# OLD (discord.py - GroupCog)
class MyCommands(commands.GroupCog, name="mygroup"):
    @app_commands.command(name="subcommand", description="...")
    async def subcommand(self, interaction: discord.Interaction) -> None:
        pass

# NEW (interactions.py)
class MyCommands(interactions.Extension):
    @interactions.slash_command(
        name="mygroup",
        description="Group description",
        sub_cmd_name="subcommand",
        sub_cmd_description="Subcommand description",
    )
    async def subcommand(self, ctx: interactions.SlashContext) -> None:
        pass
```

##### Event Listeners
```python
# OLD (discord.py)
@commands.Cog.listener()
async def on_message(self, message: discord.Message) -> None:
    pass

# NEW (interactions.py)
@interactions.listen()
async def on_message_create(self, event: interactions.events.MessageCreate) -> None:
    message = event.message
    # process message
```

##### Setup Functions
```python
# OLD (discord.py)
async def setup(bot: ForUS) -> None:
    await bot.add_cog(MyCog(bot))

# NEW (interactions.py)
def setup(bot: ForUS) -> None:
    MyCog(bot)
```

##### Options with Choices
```python
# OLD (discord.py)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Choice 1", value="val1"),
        app_commands.Choice(name="Choice 2", value="val2"),
    ]
)
async def command(self, interaction: discord.Interaction, option: app_commands.Choice[str]) -> None:
    pass

# NEW (interactions.py)
@interactions.slash_option(
    name="option",
    description="Option description",
    opt_type=interactions.OptionType.STRING,
    required=True,
    choices=[
        interactions.SlashCommandChoice(name="Choice 1", value="val1"),
        interactions.SlashCommandChoice(name="Choice 2", value="val2"),
    ],
)
async def command(self, ctx: interactions.SlashContext, option: str) -> None:
    pass
```

##### Range Types
```python
# OLD (discord.py)
async def command(self, interaction: discord.Interaction, num: app_commands.Range[int, 1, 100]) -> None:
    pass

# NEW (interactions.py)
@interactions.slash_option(
    name="num",
    description="Number between 1-100",
    opt_type=interactions.OptionType.INTEGER,
    min_value=1,
    max_value=100,
    required=True,
)
async def command(self, ctx: interactions.SlashContext, num: int) -> None:
    pass
```

##### Autocomplete
```python
# OLD (discord.py)
@command.autocomplete('param')
async def autocomplete_param(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name="suggestion", value="value")]

# NEW (interactions.py)
@command.autocomplete("param")
async def autocomplete_param(self, ctx: interactions.AutocompleteContext):
    current = ctx.input_text
    await ctx.send(choices=[
        interactions.SlashCommandChoice(name="suggestion", value="value")
    ])
```

#### 5. Test Infrastructure
- Update test files to use interactions.py types
- Fix mock objects for interactions.py

## Migration Script

A helper script `/tmp/migrate_cog.py` was created to automate basic transformations:
- Import statement migration
- Class definition (Cog -> Extension)
- Basic decorator migration
- Context parameter migration
- Type reference migration

The script creates `.bak` backups of original files.

## Known Issues

1. **Syntax Errors**: Some auto-migrated files have syntax errors that need manual fixing
2. **GroupCog Pattern**: Commands under groups need special handling with `group_name` and `sub_cmd_name`
3. **Event Names**: interactions.py uses different event names (e.g., `on_message_create` vs `on_message`)
4. **Permission Decorators**: Need to migrate `@app_commands.default_permissions()` to `default_member_permissions` parameter
5. **Autocomplete**: Different API - needs manual migration
6. **Modal Interactions**: If used, need to be updated to interactions.py modal system
7. **Button/Select Interactions**: If used, need to be updated to interactions.py component system

## Testing Strategy

After completing manual reviews:
1. Fix all syntax errors
2. Test bot startup
3. Test each command group individually
4. Test event handlers
5. Test database operations
6. Integration testing with real Discord environment

## Backups

All original files backed up with `.bak` extension:
- bot/cogs/*.py.bak
- Can be restored if needed

## Resources

- interactions.py Documentation: https://interactions-py.github.io/interactions.py/
- Migration examples in this document
- Helper script: `/tmp/migrate_cog.py`
