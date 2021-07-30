# wp3inventory
WP3 Inventory

## In Development

# Todos

## Before Public Repository

- [x] User Registration
- [ ] Improve server side email settings (send pw reset mails)
- [x] Implement Twitter API
- [x] ~~Implement Pseudo FB API~~ *Too unreliable*
- [ ] Cosmetic improvements
  - [x] Viewing sources: subunits need parsing
- [ ] Tidy up source code
  - [ ] standardize dgraph query method and usage in other functions
  - [x] remove unnecessary methods
  - [x] move non-generic dgraph methods outside of class, move into respective modules
  - [x] Turn dgraph into flask extension
  - [ ] rename modules ('records' -> 'add', 'inventory' -> 'view')
  - [x] dateparsing for dgraph objects
  - [ ] divorce HTML from JS ('newsource.html')
  - [ ] Remove external JS dependencies and collect via yarn instead
  - [ ] get rid of JQuery
- [x] Implement Account Delete feature
- [ ] Subset Fontawesome, do not load via CDN (because this sets a cookie)
- [ ] Form field options generator functions all in one file, then use caching module

## New Features


### Data entry views
- [x] new source
- [ ] New / Pending entries: only visible for reviewers and user who added entry
  - [ ] should also not appear in other queries
- [ ] new organization
- [ ] new paper
- [ ] new archive

### Data edit views

- [ ] review screen
- [ ] edit entry

### Data Queries

- [ ] add advanced query complex filters based on variables
- [x] add enter button for full text search
  - add route for full text search results
- [ ] add "report" button to detail view, add form for reporting need to edit item


### Automated Data Retrieval
- [ ] Get telegram data??
- [x] Detect RSS/XML Feeds & Sitemaps
- [ ] Get Wikidata ID: get year founded (if possible), headquarter location
- [x] Geocode Strings (e.g. Addresses) automatically via `geocode.osm('Address')`


### Performance

- [ ] investigate caching for form input fields
- [ ] caching for external assets (fontawesome, js libs)
- [ ] investigate async data processing



## User Permissions

Level | Name | Permissions
------|------|------------
0     | Anonymous | View entries
1     | Contributor  | Add entries
2     | Reviewer | + Review & Edit Entries, Invite Users
10    | Admin   | + Change User Permissions 

