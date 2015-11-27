#!/usr/bin/env python
import json
import requests
import sys
import getopt


def _jdefault(obj):
    return obj.__dict__


def load(inputfile, destination):
    json_file = open(inputfile)
    json_data = json.load(json_file)

    for i in json_data:
        data = json.dumps(i, default=_jdefault)
        print('Posting: %s' % data)
        r = requests.post(
            destination,
            data=data,
            headers={'Content-type': 'application/json'})
        print(r.status_code)

    json_file.close()


def load_singular_objects(inputfile, destination):
    parent_route, dynamic_part = destination.split('{')
    parent_route = parent_route.strip('/')
    pk_field, singlular_field = dynamic_part.split('}')
    singlular_field = singlular_field.strip('/')

    json_file = open(inputfile)
    json_data = json.load(json_file)
    objects_count = len(json_data)

    query_string = '?_limit={}'.format(objects_count)
    parent_objects = requests.get(parent_route + query_string).json()['data']

    for parent in parent_objects:
        print(parent_route)
        parent_url = parent['_self'].replace(query_string, '')
        singular_url = parent_url + '/' + singlular_field
        child = json_data.pop()
        data = json.dumps(child, default=_jdefault)
        print('Posting: {} to {}'.format(data, singular_url))
        r = requests.post(
            singular_url,
            data=data,
            headers={'Content-type': 'application/json'})
        print(r.status_code)


def main():
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'hf:u:', ['help', 'file=', 'url='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ('-f', '--file'):
            inputfile = arg
        elif opt in ('-u', '--url'):
            destination = arg

    try:
        inputfile
        destination
    except NameError:
        usage()
        sys.exit()

    if '{' in destination and not destination.endswith('}'):
        # E.g. /users/{username}/profile
        load_singular_objects(inputfile, destination)
    else:
        # E.g. /users
        load(inputfile, destination)


def usage():
    print('Usage: nefertari.post2api -f <jsonFile> -u <urlToPost>')


if __name__ == '__main__':
    main()
