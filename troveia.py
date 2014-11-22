import os
import re
import random
from flask import Flask
from flask import render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import pycountry
from wtforms import Form, SelectField, StringField, validators

from answers import questions
from credentials import TROVE_API_KEY

app = Flask(__name__)

app.secret_key = '[insert your own secret key]'

MONGO_URL = os.environ.get('MONGOHQ_URL')
 
if MONGO_URL:
	client = MongoClient(MONGO_URL)
	db = client.get_default_database()
else:
	client = MongoClient()
	db = client.troveia

class RegistrationForm(Form):
	countries = [(country.name, country.name) for country in pycountry.countries]
	team = StringField('Team name', [validators.Length(min=3, max=50)])
	list_address = StringField('Email Address', [validators.URL(require_tld=True), validators.Regexp(
    	u'http:\/\/trove\.nla\.gov\.au\/list\?id\=\d+', 
    	flags=re.IGNORECASE, 
    	message='That doesn\'t look like a Trove list url.')])
	town = StringField('Town or suburb', [validators.Length(min=3, max=50), validators.Optional()])
	state = SelectField('State', 
    	choices=[('', '---'), ('ACT', 'ACT'), ('NSW', 'NSW'), ('NT', 'NT'), ('QLD', 'QLD'), ('SA', 'SA'), ('Tas', 'Tas'), ('Vic','Vic'), ('WA', 'WA')]) 
	country = SelectField('Country', choices=countries, default='Australia')

@app.route('/')
def welcome():
    return render_template('index.html')

@app.route('/register/', methods=['GET', 'POST'])
def register():
	form = RegistrationForm(request.form)
	if request.method == 'POST' and form.validate():
		team_exists = db.teams.find_one({'team_name': form.team.data})
		if team_exists:
			form.team.errors.append('That name is already registered. Try another.')
			return render_template('register.html', form=form)
		else:
			team = {
				'team_name': form.team.data,
				'list_address': form.list_address.data,
				'town': form.town.data,
				'state': form.state.data,
				'country': form.country.data,
				'random_id': [random.random(), 0]
			}
			db.teams.save(team)
			flash('Thanks for registering!')
			return redirect(url_for('teams'))
	return render_template('register.html', form=form)

@app.route('/teams/')
def teams():
	teams = db.teams.find().sort('team_name', 1)
	return render_template('teams.html', teams=teams)

@app.route('/teams/<team_id>')
def team(team_id):
	team = db.teams.find_one({'_id': ObjectId(team_id)})
	return render_template('team.html', team=team, rounds=rounds)

@app.route('/rounds/')
def rounds():
	rounds = db.rounds.find()
	return render_template('rounds.html', rounds=rounds)

@app.route('/rounds/<int:round_num>')
def round(round_num):
	q_round = db.rounds.find_one({'number': round_num})
	return render_template('round.html', round=q_round)

@app.route('/scoreboard/')
def scoreboard():
	teams = db.teams.find().sort('score', -1)
	return render_template('scoreboard.html', teams=teams)

if __name__ == '__main__':
    app.run(debug=True)