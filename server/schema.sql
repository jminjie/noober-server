drop table if exists riders;
drop table if exists drivers;

create table riders (
  transaction_id string not null primary key,
  user_id string not null,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  counterpart_user_id string
);

create table drivers (
  transaction_id string not null primary key,
  user_id string not null,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  counterpart_user_id string
);

