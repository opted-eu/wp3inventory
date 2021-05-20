# wp3inventory
WP3 Inventory

## In Development

## User Permissions

Level | Name | Permissions
------|------|------------
0     | Anonymous | Add entries
1     | User  | Add entries
2     | Reviewer | + Review Entries, Invite Users
10    | Admin   | + Change User Permissions 


# Todos

## Data Structure 

- [ ] Soll ein entity mit mehreren Ländern in Verbindung gebracht werden, oder nur mit einem?

- [ ] Add new types "Corpus", "Annotated Data"?
- [ ] Develop edit history tracking (create duplicates? facets? )

## Features

- [ ] ~~add researchpaper title to quick search: cannot because searching multiple field names isn't working (jquery problem)~~
- [x] add enter button for full text search
        - add route for full text search results
- [ ] add "report" button to detail view, add form for reporting need to edit item

add data entry views
- [ ] new source
- [ ] new organization
- [ ] new paper
- [ ] new archive

add advanced query
- [ ] complex filters based on variables

Automated Data Retrieval
- [ ] Get Twitter Data: joined date, followers, bio/descriptions
- [ ] Get Instagram Data: joined date, followers, bio/descriptions
- [ ] Get Facebook Data: followers, bio/descriptions
- [ ] Get telegram data??
- [ ] Detect RSS/XML Feeds & Sitemaps
- [ ] Get Wikidata ID: get year founded (if possible), headquarter location
- [ ] Geocode Strings (e.g. Addresses) automatically via `geocode.osm('Address')`



## User Features

- [x] add invite new user feature
- [x] remove registration feature
- [x] add admin view to change user levels
- [ ] Enhance security: expire password reset tokens after usage

## Performance

- [ ] investigate caching for form input fields
- [ ] caching for external assets (fontawesome, js libs)
- [ ] do not include third-party libraries in this repository (e.g. use yarn to get js libs)

## Cleanup

### DGraph Class

- [ ] standardize query method and usage in other functions
- [x] remove unnecessary methods
- [x] dateparsing (also raise request)


# Server

