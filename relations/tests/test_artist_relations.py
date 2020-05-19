#!/usr/bin/env python3

import psycopg2

from get_relations import get_artist_credit_similarities, get_artist_similarities
import config


def test_artist_credits():

    relations = get_artist_credit_similarities(65)
    assert relations

    id_list = [rel['id'] for rel in relations]
    assert 963 in id_list
    assert 650 in id_list


def test_artists():

    relations = get_artist_similarities(65)
    assert relations

    id_list = [rel['id'] for rel in relations]
    assert 963 in id_list
    assert 650 in id_list
