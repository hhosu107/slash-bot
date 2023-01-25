import asyncio
import datetime
import discord
from discord.ext import commands, tasks
import logging
import os
import random
import re
import sqlite3

from dotenv import load_dotenv
from table2ascii import table2ascii as t2a, Alignment

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
const_guild_id = int(os.getenv('GUILD_ID', '0'))
# bot = discord.Bot(debug_guilds=[const_guild_id])
bot = commands.Bot(help_command=commands.DefaultHelpCommand(), debug_guilds=[const_guild_id])

# dice = bot.create_group(name="dice", description="roll dice!", guild_ids=[const_guild_id])

conn = sqlite3.connect('jokes.db')
cursor = conn.cursor()
sql = "SELECT COUNT(joke_id) FROM jokes;"
# Define grouped slash commands

# dice_bot = bot.create_group(name="dice-bot", description="dice bot")

number_of_jokes = 1
cmd_description = {
    "hello": "Dice Roller greetings you and tell a little about itself.",
    "joke": "Bot post a random DnD joke from database.",
    "rolls": f"linear sum of multiple dices and modifier. Ex) d10 5d10[-2] 2d100 fate d123[+5] Ed10[-2]"

}
missing_descriptions = f"""
            - single die, single roll: d20[+4] \
            - single die, multiple rolls: 10d4[+2] \
            - multiple dice, single roll: d4[-3] d8[-5] d20[+3] \
            - multiple dice, multiple rolls: d12[+3] 3d6[-2] 4d8[+5] \
            - fate dice: fate 4df[+2] 6dF[-5] \
            - exploding dice: explode Ed20[-4] Ed6[+1] \
            - co-co-combo: d10 5d10[-2] 2d100 date d123[+5] Ed10[-2]","""

cmd_usage = {
    "rolls": "dice_1 [dice_2 ... dice_n]"
}

@bot.event
async def on_ready():
    # log ready info
    print(datetime.datetime.now(), 'INFO', 'Bot ready')
    # log connected guilds number
    print(datetime.datetime.now(), 'INFO', 'Number of servers connected to:', bot.guilds)
    await bot.change_presence(activity=discord.Activity(name='dice rolling!',
                                                               type=discord.ActivityType.competing))
    print(const_guild_id)
    await asyncio.sleep(10)
    # start number of jokes update loop
    update_jokes.start()
    await asyncio.sleep(10)
    # start status update loop
    update_guild_number.start()

@bot.slash_command(name = "hello", description = cmd_description["hello"])
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond(f'Hello, '
                   f'my name is Dice Roller. '
                   f'I am here to help you with rolling dice. '
                   f'Please, ask "/help" to list commands with short description. '
                   f'Also, ask "/help <command_name>" for more info about each command and examples.')

"""
@dice_bot.command(name = "help", description="Command descriptions")
async def help(ctx: discord.ApplicationContext, args: str):
    help_embed = discord.Embed(title="dice-bot's help")
    command_names_list = [x.name for x in bot.commands]
    if not args:
        help_embed.add_field(
            name="List of supported commands:",
            value="\n".join([f"{i + 1}. {x.name}" for i, x in enumerate(bot.commands)]),
            inline=False
        )
        help_embed.add_field(
            name="Details",
            value="Type `/help <command name>` for more details about each command.",
            inline=False
        )
    elif args in command_names_list:
        help_embed.add_field(
            name=args,
            value=dice_bot.get_command
        )
    else:
        help_embed.add_field(
            name="Unknown command.",
            value="Unknown command."
        )
    await ctx.respond(embed=help_embed)
"""

# wrong commands handler

@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.respond(f"Command not found.\n"
                          f"Please, use the '/help' command to get full list of commands.")

# USER COMMANDS AND ERRORS HANDLERS
# JOKE COMMAND
@bot.slash_command(name="joke", description=cmd_description["joke"], guild_ids=[const_guild_id])
async def joke(ctx: discord.ApplicationContext):
    random_joke_number = random.randint(1, number_of_jokes)
    sql_joke = "SELECT joke_text FROM jokes WHERE joke_id=?;"
    cursor.execute(sql_joke, [random_joke_number])
    joke_text = cursor.fetchone()[0]
    logger.info(joke_text)
    await ctx.respond(f"Today's joke is:\n{joke_text}")

##### TODO: convert them to slash command
# TODO: convert commands to slash commands with
# discord.app_commands.CommandTree.
# https://stackoverflow.com/questions/71165431/how-do-i-make-a-working-slash-command-in-discord-py

suffix_verbs = ['pass']
mod_types = ['pass', 'add', 'sub']

limits = {
    "dice": 20,
    "edge": 1000000000,
    "mod": 1000000000,
    "adds": 3,
    "prefix": 3,
    "roll": 50
}

# FUNCTIONS
# check int
def check_int(possibly_int):
    try:
        exactly_int = int(possibly_int)
    except ValueError:
        raise commands.BadArgument
    else:
        return exactly_int


# override negative
def check_subzero(possibly_subzero):
    number = possibly_subzero
    if int(number) < 0:
        number = 0
    return number


# check zero and negative
def check_one(possibly_zero_or_less):
    if possibly_zero_or_less < 1:
        raise commands.BadArgument


# sad but we need limits
def check_limit(number, limit):
    if number > limit:
        raise commands.ArgumentParsingError


def split_dice_with_mod(dice):
    dice_split_args = re.split(r'([+-])', dice)
    adds = []
    dice_args_len = len(dice_split_args)
    dice_without_adds = dice_split_args[0]
    if dice_args_len > 1:
        adds_list = dice_split_args[1:]
        raw_adds = make_batch(adds_list, 2)
        for add in raw_adds:
            if len(add) != 2:
                raise commands.ArgumentParsingError
            if add[1] != '':
                adds.append(add)
        check_limit(len(adds), limits["adds"])
    first_dice_sign = '+'
    if len(dice_without_adds) > 0 and dice_without_adds[0] in ('+', '-'):
        first_dice_sign = dice_without_adds[0]
        dice_without_adds = dice_without_adds[1:]
    if len(dice_without_adds) > 0 and dice_without_adds[0] == 'd':
        dice_without_adds = '1' + dice_without_adds
    for i in range(len(adds)):
        if len(adds[i][1]) > 0 and adds[i][1][0] == 'd':
            adds[i][1] = 'd' + adds[i][1]
    return dice_without_adds, [first_dice_sign, dice_without_adds] + adds


# ident explode rolls
def ident_explode(rolls):
    rolls = rolls.lower()
    explode_rolls = rolls.split('e')
    if len(explode_rolls) != 2:
        raise commands.BadArgument
    number_of_rolls = explode_rolls[1]
    if number_of_rolls == '':
        number_of_rolls = 1
    number_of_rolls = check_int(number_of_rolls)
    return number_of_rolls


# split and check dice for rolls and edges
def ident_dice(dice):
    dice_type = []
    rolls_and_edges = dice.split('d')
    if len(rolls_and_edges) != 2:
        raise commands.BadArgument
    dice_rolls = rolls_and_edges[0]
    dice_edge = rolls_and_edges[1]
    if dice_rolls[0].lower() == 'e':
        explode_rolls = ident_explode(dice_rolls)
        dice_type.append('explode')
        dice_rolls = explode_rolls
        check_limit(dice_rolls, limits["roll"])
    else:
        if dice_rolls == '':
            dice_rolls = 1
        dice_rolls = check_int(dice_rolls)
        check_one(dice_rolls)
        check_limit(dice_rolls, limits["roll"])
    if dice_edge.lower() == 'f':
        dice_type.append('fate')
        dice_edge = dice_edge.upper()
    else:
        dice_edge = check_int(dice_edge)
        check_one(dice_edge)
        check_limit(dice_edge, limits["edge"])
    return dice_rolls, dice_edge, dice_type


# roll dice
def dice_roll(rolls, edge):
    dice_roll_result = []
    for counts in range(1, rolls + 1):
        roll_result = random.randint(1, edge)
        dice_roll_result.append(roll_result)
    return dice_roll_result


# fate roll
def fate_roll(rolls):
    dice_roll_result = []
    for counts in range(1, rolls + 1):
        roll_result = random.choices(["+", ".", "-"])
        dice_roll_result += roll_result
    return dice_roll_result


def fate_result(dice_result):
    total_result = dice_result.count('+') - dice_result.count('-')
    return total_result


# explode roll
def explode_roll(rolls, edge):
    if edge < 2:
        raise commands.BadArgument
    dice_roll_result = []
    for counts in range(1, rolls + 1):
        check = edge
        while check == edge:
            roll_result = random.randint(1, edge)
            dice_roll_result.append(roll_result)
            check = roll_result
    return dice_roll_result


# summarize result
def calc_result(dice_result):
    total_result = sum(dice_result)
    return total_result


# mod rolls result
def add_mod_result(total_result, mod_amount):
    total_mod_result = total_result + mod_amount
    return total_mod_result


def sub_mod_result(total_result, mod_amount):
    total_mod_result = total_result - mod_amount
    total_mod_result = check_subzero(total_mod_result)
    return total_mod_result


def sub_mod_fate(total_result, mod_amount):
    total_mod_result = total_result - mod_amount
    return total_mod_result


# create row for table output
def create_row(*args):
    table_row = []
    for item in args:
        table_row.append(item)
    return table_row


# create table from rows
def create_table(table_body):
    if len(table_body[0]) == 3:
        table_header = create_row('dice', 'rolls', 'sum')
    elif len(table_body[0]) == 4:
        table_header = create_row('dice', 'rolls', 'mods', 'sum')
    else:
        table_header = create_row('dice', 'result')
    columns = len(table_header) - 1
    output = t2a(
        header=table_header,
        body=table_body,
        first_col_heading=True,
        alignments=[Alignment.LEFT] + [Alignment.CENTER] * columns
    )
    return output


# add [] around sum number
def make_pretty_sum(not_so_pretty):
    pretty_sum = '[' + str(not_so_pretty) + ']'
    return pretty_sum


# make string from list for pretty rolls output
def make_pretty_rolls(not_so_pretty):
    delimiter = ' '
    size = 8
    pretty_rolls = ''
    if len(not_so_pretty) > size:
        batch_rolls = make_batch(not_so_pretty, size)
        for batch in batch_rolls:
            pretty_rolls += delimiter.join(str(r) for r in batch)
            pretty_rolls += '\n'
    else:
        pretty_rolls = delimiter.join(str(x) for x in not_so_pretty)
    return pretty_rolls


# let split longs for shorts
def make_batch(origin_list, size):
    new_list = []
    for i in range(0, len(origin_list), size):
        new_list.append(origin_list[i:i + size])
    return new_list


# make things shorter
def make_short(original_string, size=5):
    new_string = str(original_string)
    if len(new_string) > size:
        new_string = new_string[:2] + '..' + new_string[-1:]
    return new_string


# make dice label for table from args
def dice_maker(*args):
    args_list = list(args)
    result = ''
    if args_list[0] == 1:
        args_list = args_list[1:]
    for arg in args_list:
        result += str(arg)
    return result

# EVENTS
# on connect actions
@bot.event
async def on_connect():
    # log connection inf
    await bot.sync_commands()
    print(datetime.datetime.now(), 'INFO', 'Bot connected')


# LOOPS
# status update loop
@tasks.loop(hours=1)
async def update_guild_number():
    print(datetime.datetime.now(), 'INFO', 'Bot status updated, current number:', len(bot.guilds))
    global guilds_number
    guilds_number = len(bot.guilds)

# number of jokes update loop
@tasks.loop(hours=1)
async def update_jokes():
    cursor.execute(sql)
    global number_of_jokes
    number_of_jokes = cursor.fetchone()[0]
    print(datetime.datetime.now(), 'INFO', 'Jokes number updated, current number:', number_of_jokes)
    return number_of_jokes

# ROLLS COMMAND
@bot.slash_command(name="rolls", description=cmd_description["roll"], guild_ids=[const_guild_id])
async def rolls(ctx: discord.ApplicationContext, roll_string: str):
    roll_string = roll_string.replace(" ", "")
    logger.debug("roll called")
    logger.debug(f'{roll_string}')
    # TODO: this split eliminates + or -. Leave them to be computed.
    # Should I generate a stack calculator?
    # After `split_dice_with_mod`, we get `xdy` as `dice_raw`, and a list of
    # tuple as `adds`. For each element in `adds`, the first element is sign
    # ('+' | '-'); the second element is either a dice or constant.
    # This kind of parsing is troublesome. It doesn't recognize the following
    # type of inputs:
    # +4d6, 3+4d6, -4d6, d6, etc.
    # How can I convert?
    all_dice = re.split(r'\+|-', roll_string)
    logger.debug(f'{all_dice}')
    dice_number = len(all_dice)
    if dice_number == 0:
        await ctx.respond(f'specify valid dice, please.\n'
                       f'Try something like: ```/roll 2d8+1```')
    check_limit(dice_number, limits["dice"])
    table_body = []
    await ctx.respond(f'{all_dice}')
"""

    for dice in all_dice:

        dice_raw, adds = split_dice_with_mod(dice)
        dice_rolls, dice_edge, dice_type = ident_dice(dice_raw)
        dice_type_len = len(dice_type)

        if dice_type_len == 0:
            dice_roll_result = dice_roll(dice_rolls, dice_edge)
            result = calc_result(dice_roll_result)
        elif dice_type_len == 1 and 'fate' in dice_type:
            dice_roll_result = fate_roll(dice_rolls)
            result = fate_result(dice_roll_result)
        elif dice_type_len == 1 and 'explode' in dice_type:
            dice_roll_result = explode_roll(dice_rolls, dice_edge)
            dice_rolls = 'E' + str(dice_rolls)
            result = calc_result(dice_roll_result)
        else:
            raise commands.BadArgument

        mod_mod = []
        for add in adds:
            try:
                amount = check_int(add[1])
            except Exception:
                rolls, edge, d_type = ident_dice(add[1])
                if len(d_type) != 0:
                    raise commands.BadArgument
                d_result = dice_roll(rolls, edge)
                amount = calc_result(d_result)
            if add[0] == '+':
                result = add_mod_result(result, amount)
            if add[0] == '-':
                if 'fate' in dice_type:
                    result = sub_mod_fate(result, amount)
                else:
                    result = sub_mod_result(result, amount)
            amount_for_table = add[0] + make_short(amount)
            mod_mod.append(amount_for_table)

        table_dice = dice_maker(dice_rolls, 'd', make_short(dice_edge))
        table_dice_roll_result = make_pretty_rolls(dice_roll_result)
        table_mod_list = make_pretty_rolls(mod_mod)
        table_result = make_pretty_sum(result)

        table_row = create_row(table_dice, table_dice_roll_result, table_mod_list, table_result)
        table_body.append(table_row)

    output = create_table(table_body)
    # send it into chat
    await ctx.respond(f"```{output}```")
"""


# ROLL ERRORS HANDLER
@rolls.error
async def rolls_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.respond(f'wrong dice.\n'
                       f'Try something like: ```/roller 3d10 d10-1 3d8+1 d100-10```')
    if isinstance(error, commands.ArgumentParsingError):
        await ctx.respond(f'specify valid dice parameters, please.\n'
                       f'```Current limits:\n'
                       f'- max dice number is {limits["dice"]}\n'
                       f'- max rolls per dice is {limits["roll"]}\n'
                       f'- max dice edge is {limits["edge"]}\n'
                       f'- max number of modifiers is {limits["adds"]}\n'
                       f'- max modifier is {limits["mod"]}\n```')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond(f'specify valid dice, please.\n'
                       f'Try something like: ```/roller 2d8+1```')
    else:
        await ctx.respond(f'{error}')

# bot start
bot.run(os.getenv('TOKEN'))
# close sqlite connection
conn.close()
