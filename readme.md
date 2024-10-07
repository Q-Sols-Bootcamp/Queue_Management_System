# FastAPI Queue Management System

A FastAPI-based web application that simulates and manages user queues for different services (Deposit, Withdraw, etc.). The app includes features like queue rebalancing, user registration, and service management. It uses SQLAlchemy for database operations and includes a mechanism for dynamically managing services and counters.

## Features
- **Dynamic Queue Management:** Allows users to register for specific services and assigns them to counters.
- **Queue Rebalancing:** Automatically rebalances users between counters based on total turn-around time (TAT) to minimize wait times.
- **Service Management:** Admin can dynamically add, update, or delete services, each with a specified number of counters.
- **Counter Management:** Admins and operators can pop users from counters and trigger rescheduling of the remaining queue.
- **Average TAT Calculation:** Each queue's TAT is calculated based on the average time it takes for the counter operator to process users.
- **Detailed Logging:** Provides logs for all user processing, rescheduling, and rebalancing operations.
- **ETA Updates:** Estimated Time of Arrival (ETA) is recalculated after every user registration or when users are processed, keeping the system updated in real-time.

## How to Run

1. Clone the repository:
   ```bash
   git clone <repo-url>
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```
## API Endpoints
- **User Operations:** 
   - **POST /users/register:** Register a new user for a specific service.
   - **GET /users/{user_id}:** Retrieve information about a specific user.
- **Service Operations:** 
   - **POST /services/create:** Add a new service with a specified number of counters.
   - **PUT /services/update/{service_id}:** Update the name or counters of an existing service.
   - **DELETE /services/delete/{service_id}:** Remove a service from the system (if no users are in the queue).
- **Counter Operations:** 
   - **POST /counters/pop/{counter_id}:** Pop the next user from the counter and reschedule the queue

## Technology Stack
- FastAPI for backend
- SQLAlchemy for database operations
- Uvicorn as ASGI server
- Logging for detailed system logs
- SQLite/MySQL/PostgreSQL as database (based on your choice)

## Queue Rebalancing Algorithm
- **Turn-Around Time (TAT):** The total time taken by a counter to process users.
- **Rebalancing Trigger:** If a significant discrepancy exists between the TAT of two queues, a user is moved from the longer queue to the shorter queue.
- **Position Calculation:** The position of the user to be moved is calculated based on the formula:
  ```
  Position of user to move = ROUND(total TAT of the shorter queue / TAT of the longer queue) + 1
  ```
- **ETA Recalculation:** After any rebalancing, the ETA for each queue is updated.

## Logging
The system uses Python's logging module to keep detailed logs of every:

- User registration
- User processing (popping from a counter)
- Rebalancing between queues
- Queue state updates

## How To Contribute
1. Fork the repository
2. Create a feature branch (git checkout -b feature-branch)
3. Commit your changes (git commit -m 'Add some feature')
4. Push to the branch (git push origin feature-branch)
5. Create a pull request
