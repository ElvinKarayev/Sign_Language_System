### when you want to clear the database dont use delete but this: 
TRUNCATE TABLE users RESTART IDENTITY CASCADE;
TRUNCATE TABLE videos RESTART IDENTITY CASCADE;
TRUNCATE TABLE sentences RESTART IDENTITY CASCADE;