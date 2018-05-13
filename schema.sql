-- Table: public.reported_missing

-- DROP TABLE public.reported_missing;

CREATE TABLE public.reported_missing
(
  id integer NOT NULL DEFAULT nextval('reported_missing_id_seq'::regclass),
  filename text NOT NULL,
  resolver text NOT NULL,
  reporter text,
  "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT reported_missing_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.reported_missing
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
