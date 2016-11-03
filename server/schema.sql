drop table if exists riders;
drop table if exists drivers;

create table riders (
  user_id string not null primary key,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  matched_driver_id string,
  picked_up integer
);

create table drivers (
  user_id string not null primary key,
  lat float(10,6) not null,
  lon float(10,6) not null,
  timestamp string,
  matched_rider_id string,
  rider_in_car integer
);

