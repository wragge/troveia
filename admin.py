import click
import os
import re
import random
import requests
from pymongo import MongoClient, GEO2D
from bson.objectid import ObjectId
from nominatim import Nominatim

from answers import questions
from credentials import TROVE_API_KEY

MONGO_URL = os.environ.get('MONGOHQ_URL')
 
if MONGO_URL:
	client = MongoClient(MONGO_URL)
	db = client.get_default_database()
else:
	client = MongoClient()
	db = client.troveia

@click.group()
def admin():
	pass

@click.command()
@click.argument('round_num', type=int)
def score_round(round_num):
	db.teams.ensure_index([('random_id', GEO2D)])
	q_round =  db.rounds.find_one({'number': round_num})
	if not q_round:
		click.echo('Round {} not found!'.format(round_num))
	else:
		for team in db.teams.find({'random_id': {'$near': [random.random(), 0]}}):
			if 'results' not in team:
				team['results'] = {}
				team['score'] = 0
			score = 0
			results = {}
			click.echo('Team: {}'.format(team['team_name']))
			list_id = re.search(r'id=(\d+)', team['list_address']).group(1)
			url = 'http://api.trove.nla.gov.au/list/{}?encoding=json&reclevel=full&include=listItems&key={}'.format(list_id, TROVE_API_KEY)
			response = requests.get(url)
			try:
				json = response.json()
			except ValueError:
				click.echo('Failed to retrieve {}'.format(team['list_address']))
			else:
				items = json['list'][0]['listItem']
				links = {}
				for item in items:
					# Get the key for this item type -- work, article etc.
					try:
						for key in item.keys():
							if key != 'note':
								item_type = key
								break
						try:
							note = item['note']
						except (KeyError, AttributeError):
							note = ''
						try:
							links[item[item_type]['troveUrl']] = note
						except (KeyError, TypeError):
							pass
					#This was hastily added because of one list on Troveia night.
					#For some reason it seems item was a string...
					except AttributeError:
						pass
				for index, question in enumerate(q_round['questions']):
					results[str(index+1)] = {}
					for link in question['link']:
						if link in links:
							score += 1
							results[str(index+1)]['status'] = True
							results[str(index+1)]['link'] = link
							results[str(index+1)]['answer'] = links[link]
							click.echo('Question {} -- correct'.format(index+1))
							break
						else:
							results[str(index+1)]['status'] = False
							click.echo('Question {} -- incorrect'.format(index+1))
			team['results'][str(round_num)] = {'score': score, 'results': results}
			team['score'] = team['score'] + score
			db.teams.save(team)
		q_round['status'] = 'done'
		db.rounds.save(q_round)


@click.command()
@click.argument('round_num', type=int)
@click.option('--status', '-s', type=click.Choice(['closed', 'open', 'done']), default='closed')
def change_status(round_num, status):
	q_round =  db.rounds.find_one({'number': round_num})
	if not q_round:
		click.echo('Round {} not found!'.format(round_num))
	else:
		q_round['status'] = status
		db.rounds.save(q_round)
		click.echo('Round {} -- {} -- is {}'.format(round_num, q_round['topic'], status))

@click.command()
@click.confirmation_option(prompt='Are you sure you want to close all rounds?')
def close_rounds():
	for q_round in db.rounds.find():
		q_round['status'] = 'closed'
		db.rounds.save(q_round)
		click.echo('{} is closed'.format(q_round['topic']))

@click.command()
def load_rounds():
	click.echo('Clearing old round info...')
	db.rounds.remove()
	click.echo('Loading new round info...')
	for index, q_round in enumerate(questions):
		click.echo('Adding: {}'.format(q_round['topic']))
		q_round['status'] = 'closed'
		q_round['number'] = index + 1
		db.rounds.save(q_round)

@click.command()
@click.confirmation_option(prompt='Are you sure you want to clear all rounds info?')
def clear_rounds():
	db.rounds.remove()
	click.echo('Round info cleared...')

@click.command()
#@click.confirmation_option(prompt='Are you sure you want to clear all teams info?')
def clear_teams():
	db.teams.remove()
	click.echo('Teams info cleared...')

@click.command()
#@click.confirmation_option(prompt='Are you sure you want to clear all team scores?')
def clear_scores():
	for team in db.teams.find():
		team['results'] = {}
		team['score'] = 0
		db.teams.save(team)
	click.echo('Teams scores cleared...')

@click.command()
def locate_places():
	nom = Nominatim()
	for team in db.teams.find():
		if 'coords' not in team:
			results = nom.query('{} {} {}'.format(team['town'], team['state'], team['country']))
			place = results[0]
			team['coords'] = [float(place['lon']), float(place['lat'])]
			db.teams.save(team)
			click.echo(team['coords'])


admin.add_command(score_round)
admin.add_command(change_status)
admin.add_command(load_rounds)
admin.add_command(clear_rounds)
admin.add_command(close_rounds)
admin.add_command(clear_teams)
admin.add_command(clear_scores)
admin.add_command(locate_places)

if __name__ == '__main__':
    admin()