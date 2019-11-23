CREATE TABLE public.thanks_data
(
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  c_who character varying(45) COLLATE pg_catalog."C.UTF-8",
  c_amount numeric,
  c_to_whom character varying(45) COLLATE pg_catalog."C.UTF-8",
  c_for_what text COLLATE pg_catalog."C.UTF-8"
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.thanks_data
    OWNER to vxkhlsqjazuwxi;
