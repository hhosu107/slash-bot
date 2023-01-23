## What components do we need?

- [ ] Guild Table
  - [ ] Guild ID (string, primary key)
  - [ ] Guild Name (string)
    - [ ] If a given command returned the different guild name, update it.
- [ ] User Table
  - [ ] User ID (string, primary key)
  - [ ] User Name (string)
    - [ ] If a given command returned the different user name, update it.
- [ ] Roll Stat Table (GUID will be the primary key)
  - [ ] GUID (integer, primary key, unique per (guild id, user id))
  - [ ] Guild ID (string, foreign key)
  - [ ] User ID (string, foreign key)
  - [ ] Count of successfull `/roll` commands (integer)
  - [ ] Sum of all rolls (integer)
- [ ] Roll Log Table (Roll id will be the primary key)
  - [ ] Roll id (integer, primary key)
  - [ ] GUID (integer, foreign key)
  - [ ] Roll string (string, after symbolic computation)
  - [ ] Roll result (List; each element is a result of a single roll)
  - [ ] Roll modifier (integer)
  - [ ] Roll sum (integer)
  - [ ] Roll time (timestamp)

## How each `/roll` log accumulates to the tables?

- [ ] `/roll` command is called
- [ ] Roll string is parsed
  - [ ] If it is not a valid roll string, return error message and terminates
- [ ] Roll string is symbolically computed
- [ ] Roll each dice and get the result
- [ ] Roll modifier is added to the result
- [ ] Roll sum is computed
- [ ] Roll Log Table is appended
  - [ ] If a user does not exist in the Roll stat table, update the
      corresponding Guild Table and User Table; append the user to the
      Roll Stat Table and get GUID; otherwise, get GUID from the table
- [ ] Append the roll log to the Roll Log Table
- [ ] Sum current result to the Roll Stat Table
  - [ ] If the user does not exist in the Roll Stat Table, set count = 1 and set
      sum of all rolls as the current roll; otherwise, increment count by 1 and
      add the current roll to the sum of all rolls
