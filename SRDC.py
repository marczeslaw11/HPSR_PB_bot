from operator import truediv
import discord
from discord.ext import commands
from discord.ext import tasks
import asyncio
import srcomapi
from requests import get
from datetime import datetime as dtime
from datetime import timedelta as tdel
import math
import os
from time import sleep



def convert(t):
	hours = int(t/60/60)
	minutes = int(t/60%60)
	seconds = int(t%60)
	milliseconds = round(t%1*1000)
	if t > 600:
		return "%d:%02d:%02d" % (hours, minutes, seconds)
	else:
		return "%d:%02d.%03d" % (minutes, seconds, milliseconds) 


frequency = 5 #minutes
print(dtime.utcnow(), 'init')
Client = discord.Client(intents=discord.Intents.default())
bot_prefix= "."
client = commands.Bot(command_prefix=bot_prefix, intents=discord.Intents.default())
api = srcomapi.SpeedrunCom()
boards = {}
gamesWithVariables = {}

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])

hpSeries = get('https://www.speedrun.com/api/v1/series/15ndxp7r/games?_bulk=yes').json()['data']
sleep(0.6)
for hpGame in hpSeries:
	gameName = hpGame['names']['international']
	gameID = hpGame['id']
	hpCategories = get('https://www.speedrun.com/api/v1/games/%s/categories' % (gameID)).json()['data']
	try:
		getLastRun = get('https://www.speedrun.com/api/v1/runs?status=verified&orderby=verify-date&direction=desc&game=%s' % (gameID)).json()['data'][0]['id']
	except IndexError:
		pass
	sleep(1.2)
	variables = []
	boards[gameID] = getLastRun
	for category in hpCategories:
		categoryName = category['name']
		categoryID = category['id']
		if category['type'] == 'per-game':
			catVars = get('https://www.speedrun.com/api/v1/categories/%s/variables' % (categoryID)).json()
			sleep(0.6)
			for catVar in catVars['data']:
				if catVar['id'] not in variables and catVar['is-subcategory']:
					variables.append(catVar['id'])
	if len(variables) > 0:
		gamesWithVariables[gameName] = variables


@client.event
async def on_ready():
	print("Bot Online!")
	print("Name: {}".format(client.user.name))
	print("ID: {}".format(client.user.id))
	post.start()	


@tasks.loop(minutes = frequency)
async def post():
	channel_main = client.get_channel(597203792055894016)
	channel_test = client.get_channel(1029384953189896322)
	lastCheck = dtime.utcnow()-tdel(minutes = frequency)
	print(dtime.utcnow(), 'start')
	newRuns = []

	for board in boards:
		try:
			getRuns = get('https://www.speedrun.com/api/v1/runs?status=verified&orderby=verify-date&direction=desc&game='+board).json()['data']
			sleep(0.6)
			lastRun = boards[board] 
			newLastRun = False
			
			for run in getRuns:
				if run['id'] != lastRun:
					newRuns.append(run['id'])
					if not bool(newLastRun):
						newLastRun = run['id']					
				else:
					break
			if bool(newLastRun):
				boards[board] = newLastRun
		except:
			await channel_test.send("<@341941638681067520> category " + board + " has been deleted")

	if len(newRuns)>0:
		for newRunID in newRuns:
			getPlace = 0
			try:
				getRun = api.get("runs/"+newRunID)
				sleep(0.6)
			except srcomapi.exceptions.APIRequestException:
				await channel_test.send("<@341941638681067520> run " + newRunID + " has been deleted")
				continue
			getPlayers = ''
			getGame = api.get('games/'+getRun['game'])
			sleep(0.6)
			getGameName = getGame['names']['international']
			getGameID = getGame['id']
			getGameAbbreviation = getGame['abbreviation']
			getCategory = api.get('categories/'+getRun['category'])
			sleep(0.6)
			getCategoryName = getGameName+" "+getCategory['name']
			getCategoryID = getCategory['id']
			getTime = convert(getRun['times']['primary_t'])
			
			if getRun['level'] != None:
				continue
			
			for player in range(len(getRun['players'])):
				if player == len(getRun['players'])-1 and len(getRun['players']) > 1:
					getPlayers += ' and '
				elif player > 0:
					getPlayers += ', '
				if getRun['players'][player]['rel'] == 'user':
					getPlayers += "[%s](%s)" % (
						api.get('users/'+getRun['players'][player]['id'])['names']['international'],
						api.get('users/'+getRun['players'][player]['id'])['weblink']
					)
					sleep(1.2)
				else:
					getPlayers += api.get('users/'+getRun['players'][player]['name'])
					sleep(0.6)
			
			getLeaderboardAPI = 'https://www.speedrun.com/api/v1/leaderboards/%s/category/%s?' % (getGameID, getCategoryID)
			getLeaderboardLink = 'https://www.speedrun.com/%s?x=%s' % (getGameAbbreviation, getCategoryID)
			if getGameName in gamesWithVariables:
				for var in gamesWithVariables[getGameName]:
					try:
						getCategoryName += " "+api.get("variables/"+var)['values']['values'][getRun['values'][var]]['label']
						getLeaderboardAPI +=  "var-%s=%s&" % (var, getRun['values'][var])
						getLeaderboardLink += "-%s.%s" % (var, getRun['values'][var])
						sleep(0.6)
					except:
						getCategoryName += ''
			
			getLeaderboard = get(getLeaderboardAPI).json()['data']
			sleep(0.6)
			for runOnBoard in getLeaderboard['runs']:
				if runOnBoard['run']['id']==newRunID:
					getPlace = runOnBoard['place']
			
			try:
				if getPlace == 0:
					message = "%s got a new run in [%s](%s) with a time of [%s](%s)" % (
						getPlayers, 
						getCategoryName,
						getLeaderboardLink,
						getTime,
						api.get("runs/"+newRunID)['weblink'],
					)
				elif getPlace == 1:
					message = "<:health1st:1035612309571244032> %s got a new WR in [%s](%s) with a time of [%s](%s)" % (
						getPlayers, 
						getCategoryName,
						getLeaderboardLink,
						getTime,
						api.get("runs/"+newRunID)['weblink'],
					)
				elif getPlace == 2:
					message = "<:health2nd:1035612311412543609> %s got a new PB in [%s](%s) with a time of [%s](%s) [%s]" % (
						getPlayers, 
						getCategoryName,
						getLeaderboardLink,
						getTime,
						api.get("runs/"+newRunID)['weblink'],
						ordinal(getPlace)
					)
				elif getPlace == 3:
					message = "<:health3rd:1035612307574751254> %s got a new PB in [%s](%s) with a time of [%s](%s) [%s]" % (
						getPlayers, 
						getCategoryName,
						getLeaderboardLink,
						getTime,
						api.get("runs/"+newRunID)['weblink'],
						ordinal(getPlace)
					)				
				else:
					message = "%s got a new PB in [%s](%s) with a time of [%s](%s) [%s]" % (
						getPlayers, 
						getCategoryName,
						getLeaderboardLink,
						getTime,
						api.get("runs/"+newRunID)['weblink'],
						ordinal(getPlace)
					)
				sleep(1.2)
				messageEmbed = discord.Embed(colour=discord.Colour(0xffd700), url="https://discordapp.com", description=message)
				await channel_main.send(embed = messageEmbed)				
			except srcomapi.exceptions.APIRequestException:
				await channel_test.send("<@341941638681067520> run " + newRunID + " has been deleted")
	
	print(dtime.utcnow(), 'done')

client.run(os.getenv("DISCORD_TOKEN"))
