# Data Dictionary

Cricsheet's T20 international download in its "CSV2" format (also called Ashwin format). The full spec is at <https://cricsheet.org/format/csv_ashwin/>; this page records what I've found in the data itself. Counts are from the snapshot used in the write-ups: 4,484 matches up to 26 July 2025.

## Findings on 28/07/25

- Info files seem to contain top-level match info: the umpires, the teams, the date, the venue etc.

- The base file contains a far more in-depth outlook of a given match.

```text
match_id,season,start_date,venue,innings,ball,batting_team,bowling_team,striker,non_striker,bowler,runs_off_bat,extras,wides,noballs,byes,legbyes,penalty,wicket_type,player_dismissed,other_wicket_type,other_player_dismissed
```

```text
211028,2005,2005-06-13,The Rose Bowl,1,0.1,England,Australia,ME Trescothick,GO Jones,B Lee,0,0,,,,,,,,,
```

That is:

| match\_id | season | start\_date | venue         | innings | ball | batting\_team | bowling\_team | striker        | non\_striker | bowler | runs\_off\_bat | extras | wides | noballs | byes | legbyes | penalty | wicket\_type | player\_dismissed | other\_wicket\_type | other\_player\_dismissed |
| --------: | -----: | ----------- | ------------- | ------: | ---: | ------------- | ------------- | -------------- | ------------ | ------ | -------------: | -----: | ----: | ------: | ---: | ------: | ------: | ------------ | ----------------- | ------------------- | ------------------------ |
|    211028 |   2005 | 2005-06-13  | The Rose Bowl |       1 |  0.1 | England       | Australia     | ME Trescothick | GO Jones     | B Lee  |              0 |      0 |       |         |      |         |         |              |                   |                     |                          |

## Files

Each match is a pair of files named after its Cricinfo match ID:

| File | Contents |
| --- | --- |
| `<id>.csv` | One row per delivery, with a header row |
| `<id>_info.csv` | Match details as `info,<key>,<value>` rows, after a `version` row |

The download has 8,968 CSVs, so 4,484 matches: 2,860 men's and 1,624 women's.

## Ball-by-ball file (`<id>.csv`)

| Column | Read as | Notes |
| --- | --- | --- |
| `match_id` | text | Cricinfo match ID; joins to the info file's name |
| `season` | text | Either `2022` or a split season like `2009/10`, so not a number |
| `start_date` | date | `YYYY-MM-DD` |
| `venue` | text | Ground name. Spellings vary between matches at the same ground, e.g. `Wankhede Stadium` and `Wankhede Stadium, Mumbai` |
| `innings` | int | 1 and 2 are the main innings. **3 and up are super overs** (457 deliveries) |
| `ball` | **text** | `over.delivery`, over counted from 0. Wides and no-balls push the delivery number past 6, and an over with 10+ deliveries gives `0.10`, which **becomes `0.1` if read as a float** (1,458 deliveries). The longest over has 19 deliveries |
| `batting_team`, `bowling_team` | text | |
| `striker`, `non_striker`, `bowler` | text | Names as Cricsheet prints them. **Not unique**: use the registry IDs from the info file |
| `runs_off_bat` | int | Runs credited to the striker |
| `extras` | int | Sum of the five extras columns on this delivery |
| `wides`, `noballs`, `byes`, `legbyes`, `penalty` | int, blank when 0 | A wide or no-ball isn't a legal delivery and doesn't count towards the over |
| `wicket_type` | text | `caught`, `bowled`, `run out`, `lbw`, `stumped`, `caught and bowled`, `retired hurt`, `hit wicket`, `retired out`, `obstructing the field`, `retired not out`, `hit the ball twice` |
| `player_dismissed` | text | Can be the non-striker (run outs) |
| `other_wicket_type`, `other_player_dismissed` | text | A second dismissal on the same delivery. Only 3 rows in the whole dataset, so pandas infers them as float unless told otherwise |

### Derived rules

- **Legal delivery**: `wides` and `noballs` both blank.
- **Overs**: legal deliveries written as `overs.balls`, so 116 legal deliveries is `19.2`, not `19.33`.
- **Total runs**: `runs_off_bat + extras`.
- **Runs conceded by the bowler**: `runs_off_bat + wides + noballs`. Byes and leg byes aren't charged to the bowler.
- **Ball faced by the batter**: any delivery that isn't a wide (no-balls count as faced).
- **Wicket that falls**: `player_dismissed` set, excluding `retired hurt` and `retired not out`.
- **Wicket credited to the bowler**: `bowled`, `caught`, `caught and bowled`, `lbw`, `stumped`, `hit wicket`.

## Info file (`<id>_info.csv`)

| Key | Rows per match | Notes |
| --- | --- | --- |
| `balls_per_over` | 1 | Always 6 in this dataset |
| `team` | 2 | |
| `gender` | 1 | `male` / `female` |
| `season` | 1 | As in the ball-by-ball file |
| `date` | 1 (occasionally 2) | `YYYY/MM/DD`. 6 matches list a second date |
| `event`, `match_number` | 0-1 | Series or tournament name |
| `venue`, `city` | 1 | `city` is blank for 179 matches |
| `toss_winner`, `toss_decision` | 1 | Decision is `bat` or `field`. One match has `toss_uncontested,true` |
| `winner` | 0-1 | Missing for ties and no results |
| `winner_runs` / `winner_wickets` | 0-1 | Margin of victory |
| `outcome` | 0-1 | `tie` (43) or `no result` (85) |
| `method` | 0-1 | `D/L` (154) or `Awarded` (2) |
| `eliminator`, `bowl_out` | 0-1 | Winner of a tied match's super over or bowl-out |
| `player_of_match` | 0+ | Occasionally shared |
| `umpire`, `reserve_umpire`, `tv_umpire`, `match_referee` | 0+ | |
| `player` | 22 | `info,player,<team>,<name>`: the playing XIs |
| `players` | 0+ | `info,players,<team>,<name>`: a second player list found in 330 files. Not used yet |
| `registry` | 1 per person | `info,registry,people,<name>,<id>`: maps each name in this match to a stable Cricsheet person ID |

## Data quality notes

- **Names aren't keys.** 7,414 distinct names map to more than 7,414 people: 52 names are shared, such as four different Muhammad Usmans. Join on `(match_id, name)` to the registry to get an ID.
- **A few names don't match the registry.** A handful of strikers are spelt differently in the ball-by-ball and info files, so they need a fallback.
- **Coverage isn't complete.** Cricsheet lists missing matches on its site, so career totals can fall short of official figures.
- **Associate matches dominate recent years.** Since the ICC gave all members T20I status (women July 2018, men January 2019), most matches don't involve a full member. Segment before averaging.
