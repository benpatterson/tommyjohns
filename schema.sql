drop table if exists spreadsheets;
create table spreadsheets (
  id integer primary key autoincrement,
  googleuid text not null,
  title text not null
);
