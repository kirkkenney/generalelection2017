from flask import Flask, request, render_template
import requests
import pandas as pd
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import ColumnDataSource
from unidecode import unidecode

# election data from UK Gov. Party colours were manually appended
data = pd.read_excel('static/election_mapping.xlsx')
# data from theyworkforyou.com - for dynamically inserting links in results page
mp_names = pd.read_csv('static/names.csv')


app = Flask(__name__)


@app.route('/')
def home():
    header = 'Enter a postcode to find local results of the 2017 General Election:'
    return render_template('index.html', header=header)


@app.route('/search', methods=['POST'])
def search():
    # get string from home page form input
    postcode = request.form['postcode_lookup']
    # pass form input string to postcodes.io api (returns political/administrative data
    # in JSON fomat)
    lookup = requests.get('http://api.postcodes.io/postcodes/' + postcode)
    json_constituency = lookup.json()
    # if string input is a valid postcode in postcodes.io api
    if json_constituency['status'] == 200:
        # raw json
        unformatted_result = json_constituency['result']['parliamentary_constituency']
        # unidecode library for string formatting of eg Welsh place names
        result = unidecode(unformatted_result)
        # get election data from /static/election_mapping.xlsx as a pandas dataframe
        constituency = list(data['ConstituencyName'])
        candidate = list(data['CandidateDisplayName'])
        vote_share = list(data['ShareValue'])
        turnout = list(data['Turnout'])
        electorate = list(data['Electorate'])
        status = list(data['CandidateSatusPreElection'])
        party = list(data['CandidateParty'])
        colours = list(data['Colour'])
        # get MP names and URLs to their theyworkforyou.com profile
        mp_list = list(mp_names['Name'])
        mp_url = list(mp_names['URI'])
        # create empty variables for later assignments
        cand_result, party_result, vote_result, vote_list, colour_list, parties = [], [], [], [], [], []
        highest, winner, parliament, other_votes = 0, '', '', 0,
        # loop through wanted variables in election data
        for con, mp, party, vote, turnout, electorate, status, colour in zip(constituency, candidate, party, vote_share, turnout, electorate, status, colours):
            # if form input postcode returns a constituency name that matches a
            # constituency in dataset
            if result == con:
                # get number of eligible voters that voted
                turned_out = turnout
                electorate = electorate
                voters = (turned_out/electorate)
                # if less than 60% of eligible voters voted, dynamically change sub-heading
                # of results page
                if voters < 0.6:
                    voters_percent = 'Only ' + '{:.1%}'.format(voters)
                else:
                    voters_percent = '{:.1%}'.format(voters)
                # if vote in current loop is highest, assign it to 'highest' variable
                # (later comparative use)
                if vote > highest:
                    highest = vote
                    # assign candidate name to 'winner' variable
                    winner = mp
                # determine what text to place in a sub-heading depending on
                # whether the current MP held their seat, or defeated their predecessor
                if status == 'Title Holder' and vote == highest:
                    held_ousted = 'held'
                elif status == 'Title Holder' and vote < highest:
                    held_ousted = 'kicked %s out of' % mp
                # if the vote is less than 2% aggregate it with other sub-2% votes
                # for the purposes of data visualisation
                if vote < 0.02:
                    other_votes = other_votes + vote*100
                    party_result.append(party)
                    cand_result.append(mp)
                    vote = '{:.1%}'.format(vote)
                    vote_result.append(vote)
                    continue
                # add all matching results to new list variables and reformat to display %
                # rather than decimals
                colour_list.append(colour)
                cand_result.append(mp)
                party_result.append(party)
                vote_list.append(vote*100)
                vote = '{:.1%}'.format(vote)
                vote_result.append(vote)
                parties.append(party)
        # determine sub-heading text to display according to the victory margin
        if highest*100 >= vote_list[1]+20:
            safety = 'There\'s not much chance of %s losing at the next election' % winner
        elif vote_list[1]+5 < highest*100 < vote_list[1]+20:
            safety = 'The next election could go either way ...'
        else:
            safety = 'Too close for comfort! %s could lose next time ...' % winner
        # get theyworkforyou.com profile of winning candidate
        for mp_name, url in zip(mp_list, mp_url):
            if winner == mp_name:
                parliament = url
        # add all sub-2% votes to lists for data visualisation
        vote_list.append(other_votes)
        parties.append('Other')
        # if there are less colours than parties to display data for
        # add black as default for the lowest value party
        if len(colour_list) < len(party_result):
            colour_list.append('#000000')
        # get user platform type!
        # could not get a consisten format to display adequately on both
        # desktop and mobile devices, so have tested for platforms to amend the
        # format
        platform = request.user_agent.platform
        if platform == 'windows' or platform == 'macos' or platform == 'linux':
            source = ColumnDataSource(data=dict(parties=parties, votes=vote_list, colours=colour_list))
            p = figure(x_range=parties, y_range=(0,vote_list[0]), toolbar_location=None,
            tools='', sizing_mode='stretch_both')
            p.vbar(x='parties', top='votes', width=0.9, color='colours', source=source)
            p.grid.grid_line_color = None
            script1, div1 = components(p)
            cdn_js = CDN.js_files[0]
            cdn_css = CDN.css_files[0]
        else:
            source = ColumnDataSource(data=dict(parties=parties, votes=vote_list, colours=colour_list))
            p = figure(x_range=parties, y_range=(0,vote_list[0]), toolbar_location=None,
            tools='', sizing_mode='scale_both')
            p.vbar(x='parties', top='votes', width=0.9, color='colours', source=source)
            p.grid.grid_line_color = None
            p.title.align = 'center'
            p.xaxis.major_label_orientation = 'vertical'
            script1, div1 = components(p)
            cdn_js = CDN.js_files[0]
            cdn_css = CDN.css_files[0]
        return render_template('search.html', con_result=result,
        voters_percent=voters_percent, held_ousted=held_ousted, cand_result=cand_result,
        winner=winner, parliament=parliament, safety=safety,
        script1=script1, div1=div1, cdn_js=cdn_js, cdn_css=cdn_css,
        colour_list=colour_list, zip=zip(cand_result, party_result, vote_result))
    else:
        header = 'That didn\'t work ... want to try again?'
        return render_template('index.html', header=header)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
