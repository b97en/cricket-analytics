---
title: "Discovering Cricket Data #2"
date: 2026-10-26T12:00:00Z
draft: true
tags: ["cricket", "python", "jupyter", "data", "pandas", "matplotlib"]
categories: ["Discovering Cricket Data"]
author: "Ben Bullock"
showToc: true
TocOpen: false
weight: 2
cover:
    image: "/images/cricket.jpg"
    alt: "T20 Cricketer"
---

In [#1](/posts/projects/cricket-data/introduction/) I unpacked a single T20 international: England's six-wicket win over Pakistan in Karachi in September 2022.

This time I'm loading every match in the Cricsheet download (4,484 of them, just over a million deliveries) and asking some bigger questions:

- How fast has T20 international cricket grown?
- What does the shape of an innings look like, and has it changed?
- Does winning the toss actually matter?
- Who tops the leaderboards, and why should we be suspicious of some of them?

Before any of that, though, I have some homework to mark.

---

## Correcting my homework from #1

Looking at the whole dataset exposed a few mistakes in my first session:

1. **8,968 files isn't 8,968 matches.** Every match comes as a pair: `<id>.csv` with the ball-by-ball data and `<id>_info.csv` with the match details. That's 4,484 matches.
2. **20.7 overs isn't a thing.** I divided the number of rows by six. But wides and no-balls are re-bowled, so they don't count towards the over, and overs are written as *overs.balls*: 19.2 means 19 overs and 2 balls, not 19.2 overs as a decimal. Counting legal deliveries only, the Karachi scorecard is Pakistan 158/7 (20.0 overs) and England 160/4 (19.2 overs).
3. **The `ball` column isn't a number.** pandas read it as a float, which works until an over has ten or more deliveries. The tenth ball of the first over is `0.10`, and as a float that's the same as `0.1`.
4. **Not every wicket belongs to the bowler.** Run outs, retirements and obstructing the field all show up in `wicket_type`. A bowler's tally should only count bowled, caught, caught and bowled, lbw, stumped and hit wicket.
5. **Some matches have more than two innings.** Innings 3 and up are super overs, which need leaving out of most analysis.

I've corrected the scorecard cell in #1. The rest get fixed below.

---

## Setup

The project is on GitHub at [b97en/cricket-analytics](https://github.com/b97en/cricket-analytics). The raw data now lives in `data/` rather than the project root, and there's a `requirements.txt` and a download script:

```bash
git clone https://github.com/b97en/cricket-analytics.git
cd cricket-analytics

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/download_data.sh

jupyter lab
```

Everything below is in `model/CricketVis-Session2.ipynb`. The charts use a small styling helper, `model/plotting.py`, that draws each one in a light and a dark version.

---

## Loading everything

### Cell #1

Load every ball-by-ball file into one DataFrame. This time I tell pandas the types of the awkward columns rather than letting it guess:

```python
import csv
import glob
import os

import numpy as np
import pandas as pd

DATA_DIR = '../data/t20s_csv2'

# Every match has two files: <id>.csv (ball-by-ball) and <id>_info.csv (match info)
ball_files = sorted(f for f in glob.glob(f'{DATA_DIR}/*.csv') if not f.endswith('_info.csv'))
info_files = sorted(glob.glob(f'{DATA_DIR}/*_info.csv'))
print(f"{len(ball_files)} ball-by-ball files, {len(info_files)} info files")

# Read 'ball' as text: '0.10' (the 10th delivery of the first over) is not the same as '0.1'
dtypes = {'match_id': str, 'season': str, 'ball': str,
          'wicket_type': str, 'player_dismissed': str,
          'other_wicket_type': str, 'other_player_dismissed': str}
deliveries = pd.concat((pd.read_csv(f, dtype=dtypes) for f in ball_files), ignore_index=True)
print(f"{len(deliveries):,} deliveries loaded")
```

Output:

```text
4484 ball-by-ball files, 4484 info files
1,013,937 deliveries loaded
```

Just over a million rows in about five seconds.

### Cell #2

Here's the `ball` problem from #1 in action. Splitting the text on the `.` gives the over and the ball number separately:

```python
over_ball = deliveries['ball'].str.split('.', expand=True).astype(int)
deliveries['over'] = over_ball[0] + 1          # 1-20, the way commentators count
deliveries['ball_in_over'] = over_ball[1]

print(f"Deliveries numbered .10 or higher: {(deliveries['ball_in_over'] >= 10).sum():,}")
print(f"Read as floats, '0.10' == '0.1': {float('0.10') == float('0.1')}")

longest = deliveries.loc[deliveries['ball_in_over'].idxmax()]
print(f"\nLongest over: {longest['ball_in_over']} deliveries - {longest['bowler']} "
      f"({longest['bowling_team']} v {longest['batting_team']}, {longest['start_date']})")
```

Output:

```text
Deliveries numbered .10 or higher: 1,458
Read as floats, '0.10' == '0.1': True

Longest over: 19 deliveries - Emilia Toro (Chile v Argentina, 2023-10-14)
```

1,458 deliveries would have been mislabelled if I'd kept `ball` as a float. The record holder is Chile's Emilia Toro, who needed 19 deliveries to finish the 6th over against Argentina, 13 of them no-balls.

### Cell #3

Next, some helper columns I'll use everywhere: legal deliveries, total runs, wickets, and wickets that count for the bowler.

```python
# Wides and no-balls are re-bowled, so they don't count towards the over
deliveries['legal'] = deliveries['wides'].isna() & deliveries['noballs'].isna()
deliveries['total_runs'] = deliveries['runs_off_bat'] + deliveries['extras']

# A batter retiring hurt isn't a wicket, and run outs aren't credited to the bowler
deliveries['wicket'] = (deliveries['player_dismissed'].notna()
                        & ~deliveries['wicket_type'].isin(['retired hurt', 'retired not out']))
BOWLER_WICKETS = ['bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket']
deliveries['bowler_wicket'] = deliveries['wicket_type'].isin(BOWLER_WICKETS)

print(deliveries['wicket_type'].value_counts())
print()
print(deliveries['innings'].value_counts().sort_index())

# Innings 3 and up are super overs - keep them out of the analysis
deliveries = deliveries[deliveries['innings'] <= 2].copy()
```

Output:

```text
wicket_type
caught                   28432
bowled                   12992
run out                   5799
lbw                       4846
stumped                   2205
caught and bowled         1917
retired hurt                70
hit wicket                  51
retired out                 18
obstructing the field        7
retired not out              7
hit the ball twice           1
Name: count, dtype: int64

innings
1    546611
2    466869
3       235
4       204
5         7
6         6
7         4
8         1
Name: count, dtype: int64
```

Run outs are the third most common dismissal, so the bowler-credit fix matters. The 457 deliveries in innings 3 to 8 are super overs.

### Cell #4

The info files are a different shape. After a version line, every row is `info,<key>,<value>`, and some keys repeat: two `team` rows, a `player` row for each member of each XI, and a `registry` row giving every player and official a stable Cricsheet ID. I flatten each file into one row per match and keep the registry to one side:

```python
def read_info(path):
    """Flatten one <id>_info.csv into a dict, plus its player registry rows."""
    match = {'match_id': os.path.basename(path).removesuffix('_info.csv'), 'teams': []}
    registry = []
    with open(path, newline='') as f:
        for row in csv.reader(f):
            if row[0] != 'info':
                continue
            key = row[1]
            if key == 'team':
                match['teams'].append(row[2])
            elif key == 'registry':
                registry.append((match['match_id'], row[3], row[4]))  # info,registry,people,<name>,<id>
            elif key not in ('player', 'players', 'umpire'):
                match.setdefault(key, row[2])  # a few matches list two dates - keep the first
    return match, registry


parsed = [read_info(f) for f in info_files]
matches = pd.DataFrame([m for m, _ in parsed])
registry = pd.DataFrame([r for _, reg in parsed for r in reg], columns=['match_id', 'name', 'player_id'])

matches['date'] = pd.to_datetime(matches['date'], format='%Y/%m/%d')
matches['year'] = matches['date'].dt.year

# The 12 current ICC full members - matches between two of them are the most comparable over time
FULL_MEMBERS = {'Afghanistan', 'Australia', 'Bangladesh', 'England', 'India', 'Ireland',
                'New Zealand', 'Pakistan', 'South Africa', 'Sri Lanka', 'West Indies', 'Zimbabwe'}
matches['full_members'] = matches['teams'].apply(lambda teams: set(teams) <= FULL_MEMBERS)

print(f"{len(matches):,} matches, {matches['date'].min():%d %b %Y} to {matches['date'].max():%d %b %Y}")
print(matches['gender'].value_counts())
print(matches['outcome'].value_counts())
print(matches['method'].value_counts())
matches[['match_id', 'date', 'gender', 'teams', 'venue', 'toss_winner', 'toss_decision', 'winner']].head()
```

Output:

```text
4,484 matches, 17 Feb 2005 to 26 Jul 2025
gender
male      2860
female    1624
Name: count, dtype: int64
outcome
no result    85
tie          43
Name: count, dtype: int64
method
D/L        154
Awarded      2
Name: count, dtype: int64
  match_id       date gender                   teams  \
0  1001349 2017-02-17   male  [Australia, Sri Lanka]   
1  1001351 2017-02-19   male  [Australia, Sri Lanka]   
2  1001353 2017-02-22   male  [Australia, Sri Lanka]   
3  1004729 2016-09-05   male    [Ireland, Hong Kong]   
4  1007655 2016-06-18   male       [Zimbabwe, India]   

                               venue toss_winner toss_decision     winner  
0           Melbourne Cricket Ground   Sri Lanka         field  Sri Lanka  
1     Simonds Stadium, South Geelong   Sri Lanka         field  Sri Lanka  
2                      Adelaide Oval   Sri Lanka         field  Australia  
3  Bready Cricket Club, Magheramason   Hong Kong           bat  Hong Kong  
4                 Harare Sports Club       India         field   Zimbabwe  
```

Two things to note: 36% of these matches are women's internationals, and 154 matches had their targets set by Duckworth-Lewis. Both need handling before comparing anything.

### Cell #5

Join the match details onto every delivery and save both tables as Parquet, so later sessions don't have to re-parse 8,968 CSVs:

```python
deliveries = deliveries.merge(matches[['match_id', 'gender', 'year', 'full_members']], on='match_id')

os.makedirs('../data/processed', exist_ok=True)
deliveries.to_parquet('../data/processed/deliveries.parquet', index=False)
matches.to_parquet('../data/processed/matches.parquet', index=False)
print(f"Saved {len(deliveries):,} deliveries and {len(matches):,} matches to ../data/processed/")
```

Output:

```text
Saved 1,013,480 deliveries and 4,484 matches to ../data/processed/
```

The 154 MB of CSVs become a 5 MB Parquet file that loads in a fraction of a second.

### Cell #6

And the corrected scorecard from #1:

```python
def overs(legal_balls):
    """Cricket notation: 116 legal balls is '19.2' (19 overs and 2 balls), not 19.33."""
    return f"{legal_balls // 6}.{legal_balls % 6}"


match = deliveries[deliveries['match_id'] == '1327228']
for innings_no, inns in match.groupby('innings'):
    runs, wickets, legal = inns['total_runs'].sum(), inns['wicket'].sum(), inns['legal'].sum()
    print(f"Innings {innings_no}: {inns['batting_team'].iloc[0]} {runs}/{wickets} "
          f"in {overs(legal)} overs (run rate {runs / legal * 6:.2f})")
```

Output:

```text
Innings 1: Pakistan 158/7 in 20.0 overs (run rate 7.90)
Innings 2: England 160/4 in 19.2 overs (run rate 8.28)
```

---

## How T20 internationals took off

### Cell #7

```python
per_year = (pd.crosstab(matches['year'], matches['gender'])
            .rename(columns={'male': 'men', 'female': 'women'})[['men', 'women']])
per_year['total'] = per_year.sum(axis=1)

# How many of the men's matches were between two full members?
men_matches = matches[matches['gender'] == 'male']
per_year['men_full_v_full'] = men_matches.groupby('year')['full_members'].sum()
per_year
```

Output:

```text
gender  men  women  total  men_full_v_full
year                                      
2005      3      0      3                3
2006      8      0      8                8
2007     36      0     36               31
2008     15      0     15               12
2009     48      4     52               44
2010     56      4     60               52
2011     21      2     23               21
2012     72     32    104               61
2013     42     18     60               32
2014     58     41     99               45
2015     45     18     63               28
2016     82     36    118               59
2017     53     10     63               39
2018     74    113    187               63
2019    206    141    347               48
2020     72     49    121               43
2021    289    101    390              104
2022    444    211    655              110
2023    345    258    603               60
2024    611    348    959               96
2025    280    238    518               37
```

![Stacked columns of T20 internationals per year, men's and women's, rising from a handful in 2005 to 959 in 2024](/images/cricket-data/matches-per-year-light.png)

In April 2018 the ICC decided that every T20 match between its members would count as an international, starting in July 2018 for women and January 2019 for men. The jump is obvious: 187 matches in 2018, 347 in 2019 and 959 in 2024 (2020 is the pandemic).

The mix changed as well as the volume. In 2018, 63 of the 74 men's T20Is were between two full members. In 2024 it was 96 out of 611. Averaging "all T20Is" now mostly measures Associate cricket, so when I look at trends over time I'll stick to matches between the 12 current full members.

---

## The shape of an innings

### Cell #8

Run rate and wicket rate per over, split into the three phases of an innings and three eras:

```python
last_year = matches['year'].max()
ERAS = dict(bins=[2004, 2014, 2022, last_year], labels=['2005-14', '2015-22', f'2023-{last_year % 100:02d}'])

fm_men = deliveries[(deliveries['gender'] == 'male') & deliveries['full_members']].copy()
fm_men['era'] = pd.cut(fm_men['year'], **ERAS)
fm_men['phase'] = pd.cut(fm_men['over'], bins=[0, 6, 15, 20],
                         labels=['powerplay (1-6)', 'middle (7-15)', 'death (16-20)'])


def rates(df, by):
    g = df.groupby(by, observed=True).agg(runs=('total_runs', 'sum'), legal=('legal', 'sum'),
                                          wickets=('wicket', 'sum'))
    return pd.DataFrame({'runs_per_over': g['runs'] / g['legal'] * 6,
                         'wickets_per_over': g['wickets'] / g['legal'] * 6}).round(2)


rates(fm_men, ['era', 'phase']).unstack('phase')
```

Output:

```text
          runs_per_over                             wickets_per_over  \
phase   powerplay (1-6) middle (7-15) death (16-20)  powerplay (1-6)   
era                                                                    
2005-14            7.39          7.31          9.14             0.27   
2015-22            7.87          7.77          9.55             0.27   
2023-25            8.42          8.25          9.70             0.30   

                                     
phase   middle (7-15) death (16-20)  
era                                  
2005-14          0.28          0.54  
2015-22          0.28          0.53  
2023-25          0.31          0.55  
```

### Cell #9

The same thing over by over, comparing the earliest era with the latest:

![Line charts of runs per over and wickets per over for overs 1 to 20, 2005-14 against 2023-25](/images/cricket-data/innings-shape-light.png)

The shape is the same in both eras:

- Scoring climbs through the powerplay, while only two fielders are allowed outside the circle.
- It drops sharply in the 7th over, when the field spreads.
- It builds again to the death. The 20th over is both the most expensive over and the one where wickets fall fastest.

What's changed is the level. Batting in 2023-25 is faster in every single over: about a run an over quicker in the powerplay (7.39 to 8.42) and the middle overs (7.31 to 8.25), and half a run quicker at the death (9.14 to 9.70). Meanwhile, the wicket rate barely moved. Batters are scoring faster without getting out much more often.

### Cell #10

Does that show up in totals? First innings between full members, leaving out D/L and abandoned matches:

```python
innings = (deliveries.groupby(['match_id', 'innings'])
           .agg(team=('batting_team', 'first'), runs=('total_runs', 'sum'),
                wickets=('wicket', 'sum'), legal=('legal', 'sum'))
           .reset_index()
           .merge(matches[['match_id', 'gender', 'year', 'full_members', 'method', 'outcome',
                           'winner', 'toss_winner', 'toss_decision']], on='match_id'))

# First innings between full members, leaving out rain-affected (D/L) and abandoned matches
first = innings[(innings['innings'] == 1) & innings['full_members']
                & innings['method'].isna() & (innings['outcome'] != 'no result')].copy()
first['era'] = pd.cut(first['year'], **ERAS)
first['200_plus'] = first['runs'] >= 200

(first.groupby(['gender', 'era'], observed=True)
      .agg(innings=('runs', 'size'), average=('runs', 'mean'), median=('runs', 'median'),
           share_200_plus=('200_plus', 'mean'))
      .round(2))
```

Output:

```text
                innings  average  median  share_200_plus
gender era                                              
female 2005-14       96   116.81   115.5            0.00
       2015-22      296   133.19   133.0            0.02
       2023-25      178   139.94   141.0            0.04
male   2005-14      286   154.90   153.5            0.08
       2015-22      462   164.01   165.0            0.14
       2023-25      177   170.90   174.0            0.24
```

The average men's first innings has gone from 155 to 171, and nearly a quarter of them now pass 200. That was one in twelve before 2015. Women's totals have risen even faster, from 117 to 140, but a 200 is still rare.

---

## Does winning the toss matter?

### Cell #11

```python
# Matches with a winner, leaving out D/L results and awarded matches
decided = matches[matches['winner'].notna() & matches['method'].isna()].copy()
batted_first = innings.loc[innings['innings'] == 1, ['match_id', 'team']].rename(columns={'team': 'batted_first'})
decided = decided.merge(batted_first, on='match_id')
decided['toss_winner_won'] = decided['winner'] == decided['toss_winner']
decided['batting_first_won'] = decided['winner'] == decided['batted_first']

print(decided.groupby('gender')
             .agg(matches=('match_id', 'size'), toss_winner_won=('toss_winner_won', 'mean'),
                  batting_first_won=('batting_first_won', 'mean'))
             .round(3))

print()
print(decided.groupby(['gender', 'toss_decision'])
             .agg(matches=('match_id', 'size'), toss_winner_won=('toss_winner_won', 'mean'))
             .round(3))
```

Output:

```text
        matches  toss_winner_won  batting_first_won
gender                                             
female     1531            0.514              0.508
male       2671            0.500              0.490

                      matches  toss_winner_won
gender toss_decision                          
female bat                763            0.522
       field              768            0.507
male   bat               1249            0.489
       field             1422            0.509
```

Across 2,671 men's T20Is with a result, the team that won the toss won exactly half of them. It's 51.4% in women's matches. Batting first versus chasing is just as even. Captains do prefer to field first, but it doesn't buy much: 50.9% against 48.9% for men.

That doesn't mean the toss never matters. Dew, day/night games and particular pitches can tilt individual matches, and averaging over every ground in the world washes that out. In aggregate, though, the toss decides very little.

---

## Leaderboards, and why names aren't keys

### Cell #12

My first instinct was to group by the `striker` name. But names aren't unique:

```python
ambiguous = registry.groupby('name')['player_id'].nunique()
print(f"{len(ambiguous):,} distinct names, {(ambiguous > 1).sum()} of them shared by more than one player, e.g.")
print(ambiguous[ambiguous > 1].sort_values(ascending=False).head(5).to_string())

ids = registry.set_index(['match_id', 'name'])['player_id']


def player_ids(df, name_col):
    # A handful of names in the ball-by-ball files are spelt differently in the registry - fall back to the name
    keys = pd.MultiIndex.from_arrays([df['match_id'], df[name_col]])
    return pd.Series(ids.reindex(keys).to_numpy(), index=df.index).fillna(df[name_col])


deliveries['striker_id'] = player_ids(deliveries, 'striker')
deliveries['bowler_id'] = player_ids(deliveries, 'bowler')
deliveries['dismissed_id'] = player_ids(deliveries, 'player_dismissed')
```

Output:

```text
7,414 distinct names, 52 of them shared by more than one player, e.g.
name
Muhammad Usman    4
Haider Ali        3
Junaid Khan       3
Aminul Islam      3
Abdul Rahman      2
```

There are four different Muhammad Usmans in T20 internationals. The registry in the info files maps each (match, name) pair to a Cricsheet ID, so the leaderboards below group on IDs. A handful of names are spelt differently in the ball-by-ball and info files, so those fall back to the name.

### Cell #13

```python
def main_team(teams):
    return teams.mode().iat[0]


def batting(df):
    faced = df[df['wides'].isna()]  # a wide isn't a ball faced
    bat = faced.groupby('striker_id').agg(name=('striker', 'first'), team=('batting_team', main_team),
                                          runs=('runs_off_bat', 'sum'), balls=('runs_off_bat', 'size'))
    bat['outs'] = df[df['wicket']].groupby('dismissed_id').size().reindex(bat.index, fill_value=0)
    bat['average'] = (bat['runs'] / bat['outs'].replace(0, np.nan)).round(1)
    bat['strike_rate'] = (bat['runs'] / bat['balls'] * 100).round(1)
    return bat


def bowling(df):
    # Byes and leg byes aren't charged to the bowler; wides and no-balls are
    df = df.assign(conceded=df['runs_off_bat'] + df['wides'].fillna(0) + df['noballs'].fillna(0))
    bowl = df.groupby('bowler_id').agg(name=('bowler', 'first'), team=('bowling_team', main_team),
                                       balls=('legal', 'sum'), conceded=('conceded', 'sum'),
                                       wickets=('bowler_wicket', 'sum'))
    bowl['conceded'] = bowl['conceded'].astype(int)
    bowl['economy'] = (bowl['conceded'] / bowl['balls'] * 6).round(2)
    return bowl


for gender, label in [('male', "MEN'S"), ('female', "WOMEN'S")]:
    df = deliveries[deliveries['gender'] == gender]
    print(f"=== {label} T20I RUN SCORERS ===")
    print(batting(df).nlargest(10, 'runs').to_string(index=False))
    print(f"\n=== {label} T20I WICKET TAKERS ===")
    print(bowling(df).nlargest(10, 'wickets').to_string(index=False))
    print()
```

Output:

```text
=== MEN'S T20I RUN SCORERS ===
           name        team  runs  balls  outs  average  strike_rate
     Babar Azam    Pakistan  4172   3220   104     40.1        129.6
      RG Sharma       India  4027   2870   128     31.5        140.3
        V Kohli       India  3963   2915    82     48.3        136.0
     JC Buttler     England  3661   2481   100     36.6        147.6
     MJ Guptill New Zealand  3503   2579   110     31.8        135.8
Mohammad Rizwan    Pakistan  3386   2687    70     48.4        126.0
      DA Warner   Australia  3249   2274    96     33.8        142.9
       AJ Finch   Australia  3120   2189    91     34.3        142.5
    PR Stirling     Ireland  2934   2181   108     27.2        134.5
Virandeep Singh    Malaysia  2686   2139    75     35.8        125.6

=== MEN'S T20I WICKET TAKERS ===
             name        team  balls  conceded  wickets  economy
       TG Southee New Zealand   2729      3647      162     8.02
         IS Sodhi New Zealand   2537      3366      149     7.96
Mustafizur Rahman  Bangladesh   2226      2727      133     7.35
        AU Rashid     England   2630      3251      133     7.42
  Shakib Al Hasan  Bangladesh   2378      2744      131     6.92
       Ehsan Khan   Hong Kong   1913      2009      124     6.30
       MJ Santner New Zealand   2340      2748      124     7.05
     PWH de Silva   Sri Lanka   1596      1890      123     7.11
          A Zampa   Australia   2081      2518      117     7.26
       Haris Rauf    Pakistan   1762      2435      116     8.29

=== WOMEN'S T20I RUN SCORERS ===
        name        team  runs  balls  outs  average  strike_rate
  S Mandhana       India  3671   2915   117     31.4        125.9
   BL Mooney   Australia  3337   2638    78     42.8        126.5
    SW Bates New Zealand  3165   2881   103     30.7        109.9
    DN Wyatt     England  3129   2371   126     24.8        132.0
AC Jayangani   Sri Lanka  2984   2591   105     28.4        115.2
   NR Sciver     England  2834   2359    95     29.8        120.1
 HK Matthews West Indies  2781   2382    91     30.6        116.8
      H Kaur       India  2777   2463    95     29.2        112.7
    AJ Healy   Australia  2710   2082   100     27.1        130.2
  SFM Devine New Zealand  2620   2151    86     30.5        121.8

=== WOMEN'S T20I WICKET TAKERS ===
        name        team  balls  conceded  wickets  economy
   DB Sharma       India   2645      2714      143     6.16
S Ecclestone     England   2246      2237      142     5.98
   ML Schutt   Australia   2347      2513      141     6.42
    Nida Dar    Pakistan   2467      2456      111     5.97
 HK Matthews West Indies   1864      1927      102     6.20
    RP Yadav       India   1761      1952      101     6.65
Nahida Akter  Bangladesh   1724      1683       98     5.86
     AC Kerr New Zealand   1883      1914       95     6.10
ASS Fletcher West Indies   1767      1829       94     6.21
     KY Chan   Hong Kong   1321       990       91     4.50
```

Babar Azam and Smriti Mandhana top the run-scoring charts, and Tim Southee and Deepti Sharma the wickets. A couple of caveats:

- **Cricsheet doesn't have every match.** It lists what's missing on its site, so career totals can come up short. Rohit Sharma finished his T20I career with 4,231 runs; this dataset has 4,027 of them.
- **Associate cricket is in here too.** Malaysia's Virandeep Singh is 10th on the men's list, and Hong Kong's Ehsan Khan and KY Chan both make the bowling top tens.

---

## Small samples lie

### Cell #14

What about strike rate, the stat T20 batters are judged on?

```python
men_bat = batting(deliveries[deliveries['gender'] == 'male'])
league_sr = men_bat['runs'].sum() / men_bat['balls'].sum() * 100
print(f"{len(men_bat):,} men's batters, overall strike rate {league_sr:.1f}")

for min_balls in [1, 10, 100, 500]:
    top = men_bat[men_bat['balls'] >= min_balls].nlargest(3, 'strike_rate')
    print(f"\nHighest strike rates, minimum {min_balls} balls faced:")
    print(top[['name', 'team', 'runs', 'balls', 'strike_rate']].to_string(index=False))
```

Output:

```text
3,854 men's batters, overall strike rate 117.1

Highest strike rates, minimum 1 balls faced:
             name         team  runs  balls  strike_rate
 Noorullah Sidiqi      Belgium     6      1        600.0
         M Stoman     Portugal     6      1        600.0
Khalander Mustafa Saudi Arabia     4      1        400.0

Highest strike rates, minimum 10 balls faced:
        name                     team  runs  balls  strike_rate
    NK Yadav                    Nepal    49     18        272.2
Manan Bashir                 Bulgaria   262     98        267.3
   KRP Silva United States of America    32     12        266.7

Highest strike rates, minimum 100 balls faced:
           name    team  runs  balls  strike_rate
    Mehboob Ali   Malta   255    130        196.2
  Sahil Chauhan Estonia   413    211        195.7
Abhishek Sharma   India   535    276        193.8

Highest strike rates, minimum 500 balls faced:
       name         team  runs  balls  strike_rate
Faisal Khan Saudi Arabia  1405    818        171.8
   TH David    Australia  1301    778        167.2
   SA Yadav        India  2539   1525        166.5
```

The two highest strike rates in T20 international history belong to Noorullah Sidiqi (Belgium) and M Stoman (Portugal): 600 each, from the only ball they've faced. Raise the bar to 10 balls and the leaders change entirely, then again at 100 and at 500.

### Cell #15

Plot every batter's strike rate against how many balls they've faced and you get a funnel:

![Scatter of career strike rate against balls faced on a log scale, wide spread at low ball counts narrowing towards the average of 117](/images/cricket-data/strike-rate-funnel-light.png)

With a handful of balls, strike rates land anywhere from 0 to 600. With more evidence they converge around the overall rate of 117. Most of that spread is noise, not talent.

Minimum-balls cut-offs are a blunt fix. Everyone below the line gets thrown away, and everyone above it is treated as equally certain. A better approach is to pull each player's rate towards the average, by more when we have less evidence. That's empirical Bayes, and it's the idea behind the talent index I want to build next.

---

## Key Takeaways

- **Know the sport's rules before you trust the arithmetic.** Overs are *overs.balls*, wides and no-balls don't count towards them, and run outs aren't the bowler's.
- **Don't let pandas guess your types.** `0.10` and `0.1` are different deliveries.
- **Use IDs, not names.** 52 names in this dataset belong to more than one player.
- **Segment before you average.** T20I volume has quintupled since 2018, mostly in Associate cricket, and women's and men's matches differ.
- **Batting is faster in every over than it was a decade ago**, without many more wickets falling. Nearly a quarter of men's first innings between full members now reach 200.
- **The toss is a coin flip** in aggregate.
- **Small samples produce the wildest numbers.**

---

## What's Next?

- Build the Empirical Bayes Talent Index: shrink strike rates and economy rates towards the average, weighted by sample size.
- Adjust for opposition, so 500 balls against Associate attacks and 500 against Australia aren't treated as equal.
- Move the loading code into the Go ETL with validation schemas, ready for automated ingestion on AWS.

---

*Match data from [Cricsheet](https://cricsheet.org), available under the [Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/). Data runs to 26 July 2025.*
