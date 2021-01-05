## Explanation

Python server which manages 10 workers (which represent an ip device), listening on port 8080.
The user from the browser can ask for specific amount(1-10) of workers for a specific duration of time(sec), using this url route format:
GET-> http://localhost:8080/get_slaves?amount=3&duration=5
The server will then reutrn the ip's numbers matching the amount inserted by user, or either, if there aren't enough workers availables, 
the server return the time the user should wait, untill enough workers will be available again.
