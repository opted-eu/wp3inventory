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

## Layout

- Use Floating Labels for form input: https://getbootstrap.com/docs/5.0/forms/floating-labels/

## Features

- [ ] add researchpaper title to quick search: cannot because searching multiple field names isn't working (jquery problem)
- [x] add enter button for full text search
        - add route for full text search results

- add "report" button to detail view, add form for reporting need to edit item

## Performance

- [ ] investigate caching for form input fields

## Cleanup

### DGraph Class

- [ ] standardize query method and usage in other functions
- [ ] remove unnecessary methods
- [ ] dateparsing (also raise request)


# Server

