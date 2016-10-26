drop table if exists riders;
drop table if exists drivers;

create table riders (
  id string not null primary key,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  counterpart_id string
);

create table drivers (
  id string not null primary key,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  counterpart_id string
);

