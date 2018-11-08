-- READ THIS FIRST:
-- 
-- We need to install an extension to postgres to create uuids
-- Do this as a superuser
-- e.g. psql odometer -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
--
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sequence: public.reported_missing_id_seq

-- DROP SEQUENCE public.reported_missing_id_seq;

CREATE SEQUENCE public.reported_missing_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;
ALTER TABLE public.reported_missing_id_seq
  OWNER TO odometer;

-- Table: public.reported_missing

-- DROP TABLE public.reported_missing;

CREATE TABLE public.reported_missing
(
  id integer NOT NULL DEFAULT nextval('reported_missing_id_seq'::regclass),
  filename text NOT NULL,
  recordnumber text NOT NULL,
  musiclibrary text NOT NULL,
  "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
  resolved boolean DEFAULT false,
  CONSTRAINT reported_missing_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.reported_missing
  OWNER TO odometer;


-- Sequence: public.feedback_id_seq

-- DROP SEQUENCE public.feedback_id_seq;

CREATE SEQUENCE public.feedback_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 2
  CACHE 1;
ALTER TABLE public.feedback_id_seq
  OWNER TO odometer;

-- Table: public.feedback

-- DROP TABLE public.feedback;

CREATE TABLE public.feedback
(
  id integer NOT NULL DEFAULT nextval('feedback_id_seq'::regclass),
  "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
  public_id uuid NOT NULL DEFAULT uuid_generate_v4(),
  done boolean DEFAULT false,
  sender character varying(255),
  message text NOT NULL,
  CONSTRAINT feedback_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.feedback
  OWNER TO odometer;

-- Sequence: public.resolve_result_id_seq

-- DROP SEQUENCE public.resolve_result_id_seq;

CREATE SEQUENCE public.resolve_result_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1774
  CACHE 1;
ALTER TABLE public.resolve_result_id_seq
  OWNER TO odometer;


-- Table: public.resolve_result

-- DROP TABLE public.resolve_result;

CREATE TABLE public.resolve_result
(
  id integer NOT NULL DEFAULT nextval('resolve_result_id_seq'::regclass),
  result_code integer NOT NULL,
  result_text text NOT NULL,
  filename text NOT NULL,
  resolver text NOT NULL,
  overridden boolean DEFAULT false,
  "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT resolve_result_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.resolve_result
  OWNER TO odometer;

-- Sequence: public.license_rule_id_seq

-- DROP SEQUENCE public.license_rule_id_seq;

CREATE SEQUENCE public.license_rule_id_seq
  INCREMENT 1
  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;
ALTER TABLE public.license_rule_id_seq
  OWNER TO odometer;

-- Table: public.license_rule

-- DROP TABLE public.license_rule;

CREATE TABLE public.license_rule
(
  id integer NOT NULL DEFAULT nextval('license_rule_id_seq'::regclass),
  active boolean DEFAULT true,
  public_id uuid NOT NULL DEFAULT uuid_generate_v4(),
  "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
  source text NOT NULL,
  license_property character varying(255) NOT NULL,
  license_status character varying(255) NOT NULL,
  license_value text NOT NULL,
  comment text,
  CONSTRAINT license_rules_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.license_rule
  OWNER TO odometer;

CREATE TABLE public.discogs_result (
    id SERIAL PRIMARY KEY,
    result_code integer NOT NULL,
    result_text text NOT NULL,
    spotify_parsed_label text NOT NULL,
    discogs_label text,
    timestamp timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.discogs_result
  OWNER TO odometer;

CREATE UNIQUE INDEX discogs_result_pkey ON discogs_result(id int4_ops);

CREATE TABLE public.license_alias (
    id SERIAL PRIMARY KEY,
    property character varying(255) NOT NULL,
    value text NOT NULL,
    alias text NOT NULL,
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    public_id uuid NOT NULL DEFAULT uuid_generate_v4()
);
CREATE UNIQUE INDEX license_alias_pkey ON license_alias(id int4_ops);

CREATE TABLE dma_data_health (
    id SERIAL PRIMARY KEY,
    dma_id character varying(255) NOT NULL,
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    isrc character varying(255),
    isrc_ok boolean NOT NULL DEFAULT false,
    ean character varying(255),
    ean_ok boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX dma_data_health_pkey ON dma_data_health(id int4_ops);

CREATE TABLE copyright_lookup_result (
    id SERIAL PRIMARY KEY,
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    spotify_id character varying(255) NOT NULL,
    result character varying(255) NOT NULL,
    spotify_label text NOT NULL,
    parsed_label character varying(255) NOT NULL
);
CREATE UNIQUE INDEX copyright_lookup_result_pkey ON copyright_lookup_result(id int4_ops);