import json
import os
import random
import re
from typing import List, Set, Any

import asyncio
import datetime
import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
import logging
from sqlalchemy import select, update, insert, func
from sqlalchemy.sql import exists
import sqlite3
from table2ascii import table2ascii as t2a, Alignment

from database import models
from database.database import SessionLocal, engine

# Set logger
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Set database
models.Base.metadata.create_all(bind=engine)

load_dotenv()
const_guild_id = int(os.getenv('GUILD_ID', '0'))
# bot = discord.Bot(debug_guilds=[const_guild_id])
bot = commands.Bot(help_command=commands.DefaultHelpCommand(), debug_guilds=[const_guild_id])

# dice = bot.create_group(name="dice", description="roll dice!", guild_ids=[const_guild_id])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

conn = sqlite3.connect('jokes.db')
cursor = conn.cursor()
sql = "SELECT COUNT(joke_id) FROM jokes;"
# Define grouped slash commands

# dice_bot = bot.create_group(name="dice-bot", description="dice bot")

number_of_jokes = 1
cmd_description = {
    "hello": "Dice Roller greetings you and tell a little about itself.",
    "joke": "Bot post a random DnD joke from database.",
    "rolls": f"linear sum of multiple dices and modifier. Ex) d10 + 5d6 - 2d100 + 4 - 2d4",
    "user_stat": f"Show user's statistics.",
    "db_test": "debug"
}
missing_descriptions = f"""
            - single die, single roll: d20[+4] \
            - single die, multiple rolls: 10d4[+2] \
            - multiple dice, single roll: d4[-3] d8[-5] d20[+3] \
            - multiple dice, multiple rolls: d12[+3] 3d6[-2] 4d8[+5] \
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
    "dice": 100,
    "edge": 1000000000,
    "mod": 1000000000,
    "adds": 10,
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
    if len(dice_without_adds) > 0:
        adds.insert(0, [first_dice_sign, dice_without_adds])
    return adds

# split and check dice for rolls and edges
def ident_dice(dice):
    dice_type = []
    rolls_and_edges = dice.split('d')
    if len(rolls_and_edges) != 2:
        raise commands.BadArgument
    dice_rolls = rolls_and_edges[0]
    dice_edge = rolls_and_edges[1]
    if dice_rolls == '':
        dice_rolls = 1
    dice_rolls = check_int(dice_rolls)
    check_one(dice_rolls)
    check_limit(dice_rolls, limits["roll"])
    dice_edge = check_int(dice_edge)
    check_one(dice_edge)
    check_limit(dice_edge, limits["edge"])
    return dice_rolls, dice_edge, dice_type


# roll dice
def dice_roll(rolls, edge):
    dice_roll_result : List[int] = []
    for _ in range(1, rolls + 1):
        roll_result = random.randint(1, edge)
        dice_roll_result.append(roll_result)
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
        body=table_body[:-1],
        footer=table_body[-1],
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

# Individual roll stat command
@bot.slash_command(name="user_stat", description=cmd_description["user_stat"], guild_ids=[const_guild_id])
async def user_stat(ctx: discord.ApplicationContext):
    db = next(get_db())
    guild_id = str(ctx.guild_id)
    user_id = str(ctx.user)

    # Insert or Update guild_table
    is_exist = db.query(exists().where(models.RollStat.guild_id == guild_id, models.RollStat.user_id == user_id))
    if not is_exist:
        db.commit()
        await ctx.respond(f'```empty```')
    else:
        stmt = select(models.RollStat).filter(models.RollStat.guild_id == guild_id, models.RollStat.user_id == user_id)
        roll_stat = db.execute(stmt).scalars().one()
        db.commit()
        await ctx.respond(f'```Roll count: {roll_stat.count_successful_rolls}\nCumulative roll sum: {roll_stat.sum_successful_rolls}```')

# ROLLS COMMAND
@bot.slash_command(name="rolls", description=cmd_description["rolls"], guild_ids=[const_guild_id])
async def rolls(ctx: discord.ApplicationContext, roll_string: str):
    db = next(get_db())

    roll_string = roll_string.replace(" ", "")
    table_body = []

    adds = split_dice_with_mod(roll_string)

    mod_sum = 0
    roll_results = []  # List of tuple of (dice, List of rolls, sum)
    result = 0
    for _, add in enumerate(adds):
        try:
            amount = check_int(add[1])
            if add[0] == '+':
                mod_sum += amount
            else:
                mod_sum -= amount
        except Exception:
            rolls, edge, d_type = ident_dice(add[1])
            if len(d_type) != 0:
                raise commands.BadArgument
            d_result = dice_roll(rolls, edge)
            amount = calc_result(d_result)
            if add[0] == '-':
                amount = -1 * amount
            # Add roll row
            result = add_mod_result(result, amount)
            roll_results.append([add[0] + add[1], d_result, amount])
            table_dice = dice_maker(f'{add[0]}{rolls}', 'd', make_short(edge))
            table_dice_roll_result = make_pretty_rolls(d_result)
            table_result = make_pretty_sum(amount)
            table_row = create_row(table_dice, table_dice_roll_result, table_result)
            table_body.append(table_row)
    # Add mod row
    roll_results.append(['mod', '', mod_sum])
    result += mod_sum
    table_row = create_row('mod', '', make_pretty_sum(mod_sum))
    table_body.append(table_row)

    # Add result row
    table_row = create_row('sum', '', make_pretty_sum(result))
    table_body.append(table_row)

    output = create_table(table_body)
    print(datetime.datetime.now(), 'INFO', f'Roll {roll_string} result: {result}')

    guild_id = str(ctx.guild_id)
    guild_name = str(ctx.guild)
    user_id = str(ctx.user)
    roll_json_list = [json.dumps({'dice': row[0], 'roll_result': row[1], 'roll_sum': row[2]}) for row in roll_results]

    # Insert or Update guild_table
    stmt = select(models.GuildTable.guild_id).filter(models.GuildTable.guild_id == guild_id)
    guild_ids = db.execute(stmt).all()
    if len(guild_ids) == 0:  # Guild is not registered
        stmt = insert(models.GuildTable).values(guild_id=guild_id, guild_name=guild_name)
    else:
        stmt = update(models.GuildTable).where(models.GuildTable.guild_id == guild_id).values(guild_id=guild_id, guild_name=guild_name)
    db.execute(stmt)

    # Insert or update guild_table
    stmt = select(models.UserTable.user_id).filter(models.UserTable.user_id == user_id)
    user_ids = db.execute(stmt).all()
    if len(user_ids) == 0:
        stmt = insert(models.UserTable).values(user_id=user_id)
        db.execute(stmt)

    # Insert to roll_stat if empty
    stmt = select(models.RollStat).filter(models.RollStat.guild_id == guild_id, models.RollStat.user_id == user_id)
    roll_stat = db.execute(stmt).all()
    if len(roll_stat) == 0:
        stmt = insert(models.RollStat).values(guild_id=guild_id, user_id=user_id)
        db.execute(stmt)
    stmt = select(models.RollStat).filter(models.RollStat.guild_id == guild_id, models.RollStat.user_id == user_id)
    guid_row = db.execute(stmt).scalars().one()
    target_guid = guid_row.guid

    # Insert data to roll_log
    roll_log_stmt = insert(models.RollLog).values(guid=target_guid, roll_string=roll_string, roll_result=roll_json_list, roll_modifier=mod_sum, roll_sum=result)
    db.execute(roll_log_stmt)
    # Update roll_stat data
    curr_count_successful_rolls = guid_row.count_successful_rolls + 1
    curr_sum_successful_rolls = guid_row.sum_successful_rolls + result
    update_roll_stat_stmt = update(models.RollStat).where(models.RollStat.guid == target_guid).values(count_successful_rolls=curr_count_successful_rolls, sum_successful_rolls=curr_sum_successful_rolls)
    db.execute(update_roll_stat_stmt)

    db.commit()

    await ctx.respond(f'```{output}```')


# ROLL ERRORS HANDLER
@rolls.error
async def rolls_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.respond(f'wrong dice.\n'
                       f'Try something like: ```/rolls -3d10+3d8+1-d100```')
    if isinstance(error, commands.ArgumentParsingError):
        await ctx.respond(f'specify valid dice parameters, please.\n'
                       f'```Current limits:\n'
                       f'- max dice number is {limits["dice"]}\n'
                       f'- max dice edge is {limits["edge"]}\n'
                       f'- max number of modifiers is {limits["adds"]}\n'
                       f'- max modifier is {limits["mod"]}\n```')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.respond(f'specify valid dice, please.\n'
                       f'Try something like: ```/rolls 2d8+1```')
    else:
        await ctx.respond(f'{error}')

# bot start
bot.run(os.getenv('TOKEN'))
# close sqlite connection
conn.close()
