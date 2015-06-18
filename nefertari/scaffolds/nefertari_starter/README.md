## Installation
```
$ pip install -r requirements.txt
$ cp local.ini.template local.ini
$ nano local.ini
```
The setting `nefertari.engine` in local.ini can be set to either `nefertari_mongodb` or `nefertari_sqla`

## Run
```
$ pserve local.ini
```

### Endpoints
| uri | method(s) | description |
|-----|-----------|-------------|
| `/api/login` | POST | login w/ username, password |
| `/api/logout` | GET | logout |
| `/api/account` | POST | signup (then login) w/ username, email, password |
| `/api/users` | GET, POST, PATCH, DELETE | all users |
| `/api/users/self` | GET | currently logged-in user |
| `/api/stories` | GET, POST, PATCH, DELETE | all stories (returns only 100 records to guest users if auth = true) |
| `/api/s` | GET | endpoint dedicated to search (use with the `?q=` parameter) |

For development purposes, you can use the `_m` parameter to tunnel methods through GET in a browser.
E.g.
```
<host>/api/account?_m=POST&username=<username>&email=<email>&password=<password>
<host>/api/login?_m=POST&login=<username_or_email>&password=<password>
```
