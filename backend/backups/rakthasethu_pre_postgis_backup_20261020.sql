--
-- PostgreSQL database dump
--

\restrict lLVjJsTJYMDoAo9rFFyRjiFUdfkkcksEbsO9s5HAqdmVWCFsYOtYhTkrlNpubZt

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: blood_group_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.blood_group_enum AS ENUM (
    'A+',
    'A-',
    'B+',
    'B-',
    'AB+',
    'AB-',
    'O+',
    'O-'
);


ALTER TYPE public.blood_group_enum OWNER TO postgres;

--
-- Name: donation_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.donation_status_enum AS ENUM (
    'SCHEDULED',
    'COMPLETED',
    'CANCELLED',
    'REJECTED'
);


ALTER TYPE public.donation_status_enum OWNER TO postgres;

--
-- Name: import_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.import_status_enum AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE public.import_status_enum OWNER TO postgres;

--
-- Name: request_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.request_status_enum AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'FULFILLED',
    'CANCELLED',
    'REJECTED'
);


ALTER TYPE public.request_status_enum OWNER TO postgres;

--
-- Name: request_urgency_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.request_urgency_enum AS ENUM (
    'NORMAL',
    'URGENT',
    'CRITICAL'
);


ALTER TYPE public.request_urgency_enum OWNER TO postgres;

--
-- Name: user_role_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_role_enum AS ENUM (
    'SUPER_ADMIN',
    'HOSPITAL_ADMIN',
    'STAFF'
);


ALTER TYPE public.user_role_enum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: blood_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blood_requests (
    id integer NOT NULL,
    request_code character varying(32) NOT NULL,
    hospital_id integer NOT NULL,
    patient_name character varying(150) NOT NULL,
    blood_group public.blood_group_enum NOT NULL,
    units_requested integer DEFAULT 1 NOT NULL,
    district character varying(100) NOT NULL,
    location character varying(255),
    contact_phone character varying(20) NOT NULL,
    emergency_contact character varying(20),
    required_date date NOT NULL,
    urgency public.request_urgency_enum DEFAULT 'NORMAL'::public.request_urgency_enum NOT NULL,
    status public.request_status_enum DEFAULT 'PENDING'::public.request_status_enum NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_units_requested_positive CHECK ((units_requested > 0))
);


ALTER TABLE public.blood_requests OWNER TO postgres;

--
-- Name: blood_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.blood_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.blood_requests_id_seq OWNER TO postgres;

--
-- Name: blood_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.blood_requests_id_seq OWNED BY public.blood_requests.id;


--
-- Name: donations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donations (
    id integer NOT NULL,
    donation_code character varying(32) NOT NULL,
    donor_id integer NOT NULL,
    hospital_id integer,
    donation_date date NOT NULL,
    donation_type character varying(50) DEFAULT 'Voluntary'::character varying NOT NULL,
    units_donated integer DEFAULT 1 NOT NULL,
    status public.donation_status_enum DEFAULT 'COMPLETED'::public.donation_status_enum NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_units_donated_positive CHECK ((units_donated > 0))
);


ALTER TABLE public.donations OWNER TO postgres;

--
-- Name: donations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.donations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.donations_id_seq OWNER TO postgres;

--
-- Name: donations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.donations_id_seq OWNED BY public.donations.id;


--
-- Name: donor_import_batches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donor_import_batches (
    id integer NOT NULL,
    batch_code character varying(32) NOT NULL,
    hospital_id integer,
    uploaded_by_user_id integer,
    filename character varying(255) NOT NULL,
    file_format character varying(10) DEFAULT 'csv'::character varying NOT NULL,
    total_records integer DEFAULT 0 NOT NULL,
    successful_records integer DEFAULT 0 NOT NULL,
    failed_records integer DEFAULT 0 NOT NULL,
    status public.import_status_enum DEFAULT 'PENDING'::public.import_status_enum NOT NULL,
    error_summary text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp with time zone
);


ALTER TABLE public.donor_import_batches OWNER TO postgres;

--
-- Name: donor_import_batches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.donor_import_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.donor_import_batches_id_seq OWNER TO postgres;

--
-- Name: donor_import_batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.donor_import_batches_id_seq OWNED BY public.donor_import_batches.id;


--
-- Name: donors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donors (
    id integer NOT NULL,
    donor_code character varying(32) NOT NULL,
    hospital_id integer,
    full_name character varying(150) NOT NULL,
    blood_group public.blood_group_enum NOT NULL,
    gender character varying(20),
    phone character varying(20) NOT NULL,
    email character varying(120),
    district character varying(100) NOT NULL,
    panchayat character varying(100),
    address text,
    is_active boolean DEFAULT true NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.donors OWNER TO postgres;

--
-- Name: donors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.donors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.donors_id_seq OWNER TO postgres;

--
-- Name: donors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.donors_id_seq OWNED BY public.donors.id;


--
-- Name: hospitals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hospitals (
    id integer NOT NULL,
    hospital_code character varying(32) NOT NULL,
    name character varying(255) NOT NULL,
    hospital_type character varying(50) DEFAULT 'Government'::character varying NOT NULL,
    district character varying(100) NOT NULL,
    panchayat character varying(100),
    address text NOT NULL,
    phone character varying(20),
    email character varying(120),
    emergency_number character varying(20),
    latitude double precision,
    longitude double precision,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.hospitals OWNER TO postgres;

--
-- Name: hospitals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.hospitals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hospitals_id_seq OWNER TO postgres;

--
-- Name: hospitals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.hospitals_id_seq OWNED BY public.hospitals.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    user_code character varying(32) NOT NULL,
    hospital_id integer,
    email character varying(120) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(150) NOT NULL,
    phone_number character varying(20),
    role public.user_role_enum DEFAULT 'STAFF'::public.user_role_enum NOT NULL,
    district character varying(100),
    panchayat character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: blood_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blood_requests ALTER COLUMN id SET DEFAULT nextval('public.blood_requests_id_seq'::regclass);


--
-- Name: donations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donations ALTER COLUMN id SET DEFAULT nextval('public.donations_id_seq'::regclass);


--
-- Name: donor_import_batches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donor_import_batches ALTER COLUMN id SET DEFAULT nextval('public.donor_import_batches_id_seq'::regclass);


--
-- Name: donors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donors ALTER COLUMN id SET DEFAULT nextval('public.donors_id_seq'::regclass);


--
-- Name: hospitals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hospitals ALTER COLUMN id SET DEFAULT nextval('public.hospitals_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
7a17b6da95a4
\.


--
-- Data for Name: blood_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.blood_requests (id, request_code, hospital_id, patient_name, blood_group, units_requested, district, location, contact_phone, emergency_contact, required_date, urgency, status, notes, created_at, updated_at) FROM stdin;
59	BR001	46	Baby of Soumya (NICU Bed 3)	O+	2	Kottayam	Kottayam Medical College NICU	+919447111222	+919447333444	2026-09-24	CRITICAL	PENDING	Emergency neonatal exchange transfusion required immediately. Crossmatching ready.	2026-09-24 17:53:14.720918+00	2026-09-24 17:53:14.720923+00
60	BR002	46	Sreedharan Pillai (Orthopedic Surgery)	A+	1	Kottayam	Kottayam Medical College OT 4	+919447222333	+919447444555	2026-09-25	URGENT	IN_PROGRESS	Elective hip replacement surgery planned for tomorrow morning.	2026-09-24 17:53:14.720924+00	2026-09-24 17:53:14.720924+00
61	BR003	47	Anitha Paul (Postpartum Hemorrhage)	B+	3	Ernakulam	General Hospital Ernakulam Labour Room	+919447555666	+919447777888	2026-09-24	CRITICAL	PENDING	High priority emergency request for labor room hemorrhage.	2026-09-24 17:53:14.720925+00	2026-09-24 17:53:14.720925+00
62	BR004	47	Master Devansh (Thalassemia Support)	O-	1	Ernakulam	General Hospital Ernakulam Day Care	+919447888999	+919447999000	2026-09-26	URGENT	IN_PROGRESS	Routine monthly transfusion for thalassemia major patient. Needs filtered blood.	2026-09-24 17:53:14.720926+00	2026-09-24 17:53:14.720927+00
63	BR005	48	Kunjali Marakkar (Cardiothoracic ICU)	A-	2	Kozhikode	GMC Kozhikode CTVS ICU	+919895111222	+919895333444	2026-09-25	CRITICAL	PENDING	Coronary artery bypass grafting surgery scheduled.	2026-09-24 17:53:14.720927+00	2026-09-24 17:53:14.720928+00
64	BR006	49	Radha Madhavan (Oncology Support)	AB+	2	Thiruvananthapuram	Regional Cancer Centre Ward 3	+919447666777	+919447888111	2026-09-26	NORMAL	PENDING	Chemotherapy induced thrombocytopenia support.	2026-09-24 17:53:14.720928+00	2026-09-24 17:53:14.720929+00
65	BR007	49	Venu Gopal (Accident Trauma)	O+	1	Thiruvananthapuram	GMC Thiruvananthapuram Emergency Wing	+919447999111	+919447222888	2026-09-22	NORMAL	FULFILLED	Patient successfully received 1 unit whole blood from voluntary replacement.	2026-09-24 17:53:14.720929+00	2026-09-24 17:53:14.72093+00
\.


--
-- Data for Name: donations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.donations (id, donation_code, donor_id, hospital_id, donation_date, donation_type, units_donated, status, notes, created_at) FROM stdin;
66	DN001	290	46	2026-05-27	Whole Blood	1	COMPLETED	Voluntary donation at Kottayam Medical College Blood Bank. Normal vitals.	2026-09-24 17:53:14.705588+00
67	DN002	291	46	2026-06-16	Whole Blood	1	COMPLETED	Camp donation at Pala St. Thomas College.	2026-09-24 17:53:14.705594+00
68	DN003	296	46	2026-09-04	Whole Blood	1	COMPLETED	Replacement donation for cardiac patient.	2026-09-24 17:53:14.705595+00
69	DN004	297	47	2026-04-27	Whole Blood	1	COMPLETED	Voluntary donation at Ernakulam General Hospital.	2026-09-24 17:53:14.705596+00
70	DN005	303	48	2026-09-27	Whole Blood	1	SCHEDULED	Scheduled appointment at Kozhikode Medical College Blood Bank.	2026-09-24 17:53:14.705597+00
\.


--
-- Data for Name: donor_import_batches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.donor_import_batches (id, batch_code, hospital_id, uploaded_by_user_id, filename, file_format, total_records, successful_records, failed_records, status, error_summary, created_at, completed_at) FROM stdin;
51	BATCH-00051	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:51:49.827067+00	2026-09-24 17:51:49.894849+00
55	BATCH-00055	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:52:59.851522+00	2026-09-24 17:53:00.016225+00
59	BATCH-00059	\N	19	kerala_hospital_donors.csv	csv	8	8	0	COMPLETED	\N	2026-09-25 04:48:52.722894+00	2026-09-25 04:48:53.002049+00
60	BATCH-00060	\N	19	kerala_hospital_donors.csv	csv	8	8	0	COMPLETED	\N	2026-09-25 09:55:40.087214+00	2026-09-25 09:55:40.230726+00
52	BATCH-00052	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:51:50.303499+00	2026-09-24 17:51:50.35982+00
56	BATCH-00056	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:53:00.962896+00	2026-09-24 17:53:01.157702+00
53	BATCH-00053	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:51:50.662816+00	2026-09-24 17:51:50.726404+00
7	BATCH-00007	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 16:47:32.043681+00	2026-09-24 16:47:32.116108+00
3	BATCH-00003	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94839634311'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:46:36.439028+00	2026-09-24 16:46:36.489905+00
6	BATCH-00006	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94842468211'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:47:04.775671+00	2026-09-24 16:47:04.826832+00
10	BATCH-00010	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94845326911'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:47:33.363993+00	2026-09-24 16:47:33.416202+00
14	BATCH-00014	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94849604211'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:48:16.134767+00	2026-09-24 16:48:16.187084+00
18	BATCH-00018	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94875866411'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:52:38.802498+00	2026-09-24 16:52:38.926926+00
22	BATCH-00022	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94880489811'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:53:25.04937+00	2026-09-24 16:53:25.193315+00
26	BATCH-00026	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94883969111'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:53:59.876199+00	2026-09-24 16:54:00.018162+00
30	BATCH-00030	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94927341911'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:01:13.512936+00	2026-09-24 17:01:13.569298+00
34	BATCH-00034	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94963903211'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:07:19.128733+00	2026-09-24 17:07:19.179864+00
38	BATCH-00038	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94967450511'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:07:54.598106+00	2026-09-24 17:07:54.652561+00
42	BATCH-00042	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94969930511'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:08:19.398631+00	2026-09-24 17:08:19.452401+00
46	BATCH-00046	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94974526311'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:09:05.355688+00	2026-09-24 17:09:05.406588+00
50	BATCH-00050	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94163857611'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:40:38.669398+00	2026-09-24 17:40:38.722809+00
1	BATCH-00001	\N	\N	donors_import.csv	csv	2	0	2	FAILED	Row 2: Invalid phone number format: '97839546211'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).\nRow 3: Invalid phone number format: '97839546222'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:46:35.509703+00	2026-09-24 16:46:35.563077+00
2	BATCH-00002	\N	\N	donors_excel.xlsx	xlsx	2	0	2	FAILED	Row 2: Invalid phone number format: '95839589611'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).\nRow 3: Invalid phone number format: '95839589622'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:46:35.974263+00	2026-09-24 16:46:36.024126+00
4	BATCH-00004	\N	\N	donors_import.csv	csv	2	0	2	FAILED	Row 2: Invalid phone number format: '974238221'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).\nRow 3: Invalid phone number format: '974238222'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:47:03.870197+00	2026-09-24 16:47:03.924978+00
5	BATCH-00005	\N	\N	donors_excel.xlsx	xlsx	2	0	2	FAILED	Row 2: Invalid phone number format: '954242501'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).\nRow 3: Invalid phone number format: '954242502'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 16:47:04.318229+00	2026-09-24 16:47:04.369531+00
8	BATCH-00008	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 16:47:32.495922+00	2026-09-24 16:47:32.554321+00
9	BATCH-00009	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 16:47:32.835612+00	2026-09-24 16:47:32.900233+00
11	BATCH-00011	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 16:48:14.838616+00	2026-09-24 16:48:14.90492+00
12	BATCH-00012	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 16:48:15.271785+00	2026-09-24 16:48:15.331536+00
13	BATCH-00013	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 16:48:15.612478+00	2026-09-24 16:48:15.675482+00
15	BATCH-00015	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 16:52:36.387739+00	2026-09-24 16:52:36.55653+00
16	BATCH-00016	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 16:52:37.235496+00	2026-09-24 16:52:37.375376+00
17	BATCH-00017	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 16:52:37.941651+00	2026-09-24 16:52:38.082197+00
19	BATCH-00019	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 16:53:22.632248+00	2026-09-24 16:53:22.858749+00
20	BATCH-00020	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 16:53:23.534399+00	2026-09-24 16:53:23.621958+00
21	BATCH-00021	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 16:53:24.087568+00	2026-09-24 16:53:24.22164+00
23	BATCH-00023	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 16:53:57.528236+00	2026-09-24 16:53:57.671854+00
24	BATCH-00024	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 16:53:58.216438+00	2026-09-24 16:53:58.35092+00
25	BATCH-00025	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 16:53:58.848652+00	2026-09-24 16:53:58.961856+00
27	BATCH-00027	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:01:12.131824+00	2026-09-24 17:01:12.200203+00
28	BATCH-00028	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:01:12.604754+00	2026-09-24 17:01:12.664163+00
29	BATCH-00029	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:01:12.965247+00	2026-09-24 17:01:13.030027+00
31	BATCH-00031	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:07:17.665191+00	2026-09-24 17:07:17.733833+00
32	BATCH-00032	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:07:18.160562+00	2026-09-24 17:07:18.230516+00
33	BATCH-00033	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:07:18.568431+00	2026-09-24 17:07:18.638778+00
35	BATCH-00035	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:07:53.24501+00	2026-09-24 17:07:53.312567+00
36	BATCH-00036	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:07:53.692491+00	2026-09-24 17:07:53.750665+00
37	BATCH-00037	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:07:54.060286+00	2026-09-24 17:07:54.127513+00
47	BATCH-00047	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:40:37.178933+00	2026-09-24 17:40:37.248654+00
48	BATCH-00048	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:40:37.679762+00	2026-09-24 17:40:37.739763+00
49	BATCH-00049	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:40:38.097426+00	2026-09-24 17:40:38.162084+00
57	BATCH-00057	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:53:01.722627+00	2026-09-24 17:53:01.806027+00
39	BATCH-00039	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:08:18.07583+00	2026-09-24 17:08:18.14036+00
40	BATCH-00040	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:08:18.508418+00	2026-09-24 17:08:18.564497+00
41	BATCH-00041	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:08:18.851127+00	2026-09-24 17:08:18.918756+00
43	BATCH-00043	\N	\N	donors_import.csv	csv	2	2	0	COMPLETED	\N	2026-09-24 17:09:04.008276+00	2026-09-24 17:09:04.074431+00
44	BATCH-00044	\N	\N	donor_update.csv	csv	1	1	0	COMPLETED	\N	2026-09-24 17:09:04.446566+00	2026-09-24 17:09:04.50884+00
45	BATCH-00045	\N	\N	donors_excel.xlsx	xlsx	2	2	0	COMPLETED	\N	2026-09-24 17:09:04.809361+00	2026-09-24 17:09:04.878992+00
54	BATCH-00054	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94231122711'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:51:51.333326+00	2026-09-24 17:51:51.387624+00
58	BATCH-00058	\N	\N	authorized.csv	csv	1	0	1	FAILED	Row 2: Invalid phone number format: '94238260911'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX).	2026-09-24 17:53:02.715225+00	2026-09-24 17:53:02.776803+00
\.


--
-- Data for Name: donors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.donors (id, donor_code, hospital_id, full_name, blood_group, gender, phone, email, district, panchayat, address, is_active, is_available, created_at, updated_at) FROM stdin;
317	DON00028	\N	Pranav Mohan	O+	Male	+919847112233	pranav.m@example.com	Kottayam	Ettumanoor	Cheruvallil House Ettumanoor	t	t	2026-09-25 04:48:52.852903+00	2026-09-25 04:48:52.852921+00
318	DON00029	\N	Athira Krishna	A+	Female	+919847223344	athira.k@example.com	Kottayam	Pala	Krishnavilasam Pala	t	t	2026-09-25 04:48:52.881251+00	2026-09-25 04:48:52.881268+00
319	DON00030	\N	Bibin K Baby	B+	Male	+919847334455	bibin.b@example.com	Kottayam	Kanjirappally	Kallunkal House Kanjirappally	t	t	2026-09-25 04:48:52.898648+00	2026-09-25 04:48:52.898671+00
320	DON00031	\N	Fahad V N	O-	Male	+919847445566	fahad.vn@example.com	Kottayam	Changanassery	Valiyaveettil Changanassery	t	t	2026-09-25 04:48:52.918431+00	2026-09-25 04:48:52.91844+00
321	DON00032	\N	Saritha R	AB+	Female	+919847556677	saritha.r@example.com	Kottayam	Vaikom	Kulangara House Vaikom	t	t	2026-09-25 04:48:52.937011+00	2026-09-25 04:48:52.93703+00
322	DON00033	\N	Deepak P	A-	Male	+919847667788	deepak.p@example.com	Ernakulam	Aluva	Periyar View Aluva	t	t	2026-09-25 04:48:52.957268+00	2026-09-25 04:48:52.95729+00
323	DON00034	\N	Treesa Scaria	B-	Female	+919847778899	treesa.s@example.com	Ernakulam	Angamaly	Kottackal House Angamaly	t	t	2026-09-25 04:48:52.977421+00	2026-09-25 04:48:52.977439+00
324	DON00035	\N	Sanjay R	O+	Male	+919847889900	sanjay.r@example.com	Ernakulam	Kakkanad	SmartCity Road Kakkanad	t	t	2026-09-25 04:48:52.997182+00	2026-09-25 04:48:52.997195+00
290	DNR001	46	Rahul Nair	O+	Male	+919847012345	rahul.nair@example.com	Kottayam	Kumarakom	Nalukettu House, Kumarakom PO, Kottayam	t	t	2026-09-24 17:53:14.686479+00	2026-09-24 17:53:14.686488+00
291	DNR002	46	Anjali Menon	A+	Female	+919847123456	anjali.menon@example.com	Kottayam	Pala	Menon Villa, Pala Town, Kottayam	t	t	2026-09-24 17:53:14.686489+00	2026-09-24 17:53:14.68649+00
292	DNR003	46	Mathew Joseph	B+	Male	+919847234567	mathew.joseph@example.com	Kottayam	Changanassery	Kavalam House, Changanassery	t	t	2026-09-24 17:53:14.68649+00	2026-09-24 17:53:14.686491+00
293	DNR004	46	Sneha Thomas	AB+	Female	+919847345678	sneha.thomas@example.com	Kottayam	Ettumanoor	Rose Garden, Ettumanoor, Kottayam	t	t	2026-09-24 17:53:14.686492+00	2026-09-24 17:53:14.686492+00
294	DNR005	46	Arun Kumar S	O-	Male	+919847456789	arun.ks@example.com	Kottayam	Kanjirappally	Thamarassery House, Kanjirappally	t	t	2026-09-24 17:53:14.686493+00	2026-09-24 17:53:14.686494+00
295	DNR006	46	Reshma Varghese	A-	Female	+919847567890	reshma.v@example.com	Kottayam	Vaikom	Lake View, Vaikom West	t	t	2026-09-24 17:53:14.686494+00	2026-09-24 17:53:14.686495+00
296	DNR007	46	George Kurian	O+	Male	+919847678901	george.k@example.com	Kottayam	Pala	Kurian Villa, Lalam, Pala	t	t	2026-09-24 17:53:14.686496+00	2026-09-24 17:53:14.686496+00
297	DNR008	47	Muhammed Bilal	O+	Male	+919846012345	bilal.m@example.com	Ernakulam	Aluva	Periyar Nagar, Aluva, Ernakulam	t	t	2026-09-24 17:53:14.686497+00	2026-09-24 17:53:14.686498+00
298	DNR009	47	Divya Pillai	B+	Female	+919846123456	divya.pillai@example.com	Ernakulam	Kakkanad	Infopark Express Way, Kakkanad	t	t	2026-09-24 17:53:14.686498+00	2026-09-24 17:53:14.686499+00
299	DNR010	47	Akhil George	A+	Male	+919846234567	akhil.george@example.com	Ernakulam	Angamaly	St. George Avenue, Angamaly	t	t	2026-09-24 17:53:14.6865+00	2026-09-24 17:53:14.686501+00
300	DNR011	47	Neha Nambiar	O-	Female	+919846345678	neha.nambiar@example.com	Ernakulam	Tripunithura	Statue Junction, Tripunithura	t	t	2026-09-24 17:53:14.686501+00	2026-09-24 17:53:14.686502+00
301	DNR012	47	Vishnu Das	AB-	Male	+919846456789	vishnu.das@example.com	Ernakulam	Perumbavoor	AM Road, Perumbavoor	t	t	2026-09-24 17:53:14.686503+00	2026-09-24 17:53:14.686504+00
302	DNR013	47	Fatima Zahra	B-	Female	+919846567890	fatima.z@example.com	Ernakulam	Muvattupuzha	Market Road, Muvattupuzha	t	t	2026-09-24 17:53:14.686505+00	2026-09-24 17:53:14.686506+00
303	DNR014	48	Jamsheer K	O+	Male	+919895012345	jamsheer.k@example.com	Kozhikode	Feroke	Chungam, Feroke, Kozhikode	t	t	2026-09-24 17:53:14.686507+00	2026-09-24 17:53:14.686507+00
304	DNR015	48	Aparna Ramesh	B+	Female	+919895123456	aparna.r@example.com	Kozhikode	Vadakara	Temple Road, Vadakara	t	t	2026-09-24 17:53:14.686508+00	2026-09-24 17:53:14.686509+00
305	DNR016	48	Sreejith K P	A+	Male	+919895234567	sreejith.kp@example.com	Kozhikode	Koyilandy	Beach Road, Koyilandy	t	t	2026-09-24 17:53:14.68651+00	2026-09-24 17:53:14.686511+00
306	DNR017	48	Nandana S	O-	Female	+919895345678	nandana.s@example.com	Kozhikode	Balussery	Balussery Mukku, Kozhikode	t	t	2026-09-24 17:53:14.686512+00	2026-09-24 17:53:14.686513+00
307	DNR018	48	Fayis Ahmed	AB+	Male	+919895456789	fayis.a@example.com	Kozhikode	Ramanattukara	Airport Road, Ramanattukara	t	t	2026-09-24 17:53:14.686514+00	2026-09-24 17:53:14.686514+00
308	DNR019	49	Gokul Krishna	O+	Male	+919447012345	gokul.k@example.com	Thiruvananthapuram	Kazhakkoottam	Technopark Phase 1, Kazhakkoottam	t	t	2026-09-24 17:53:14.686515+00	2026-09-24 17:53:14.686515+00
309	DNR020	49	Lekshmi B	A+	Female	+919447123456	lekshmi.b@example.com	Thiruvananthapuram	Attingal	Palace Road, Attingal	t	t	2026-09-24 17:53:14.686516+00	2026-09-24 17:53:14.686517+00
310	DNR021	49	Sarath Chandran	B+	Male	+919447234567	sarath.c@example.com	Thiruvananthapuram	Neyyattinkara	TB Junction, Neyyattinkara	t	t	2026-09-24 17:53:14.686518+00	2026-09-24 17:53:14.686518+00
311	DNR022	49	Keerthi Mohan	O-	Female	+919447345678	keerthi.m@example.com	Thiruvananthapuram	Nedumangad	Koyikkal, Nedumangad	t	t	2026-09-24 17:53:14.686519+00	2026-09-24 17:53:14.68652+00
312	DNR023	52	Harikrishnan P	O+	Male	+919496012345	hari.kp@example.com	Thrissur	Guruvayur	East Nada, Guruvayur, Thrissur	t	t	2026-09-24 17:53:14.68652+00	2026-09-24 17:53:14.686521+00
313	DNR024	52	Meera Warrier	B+	Female	+919496123456	meera.w@example.com	Thrissur	Irinjalakuda	Koodalmanikyam Road, Irinjalakuda	t	t	2026-09-24 17:53:14.686522+00	2026-09-24 17:53:14.686523+00
314	DNR025	50	Manikandan R	O+	Male	+919446012345	mani.r@example.com	Palakkad	Ottapalam	Main Road, Ottapalam, Palakkad	t	t	2026-09-24 17:53:14.686524+00	2026-09-24 17:53:14.686524+00
315	DNR026	51	Vipin V	A+	Male	+919567012345	vipin.v@example.com	Alappuzha	Cherthala	Court Road, Cherthala, Alappuzha	t	t	2026-09-24 17:53:14.686526+00	2026-09-24 17:53:14.686526+00
316	DNR027	53	Abhiram M	O+	Male	+919400123456	abhiram.m@example.com	Wayanad	Kalpetta	Pinangode Road, Kalpetta, Wayanad	t	t	2026-09-24 17:53:14.686527+00	2026-09-24 17:53:14.686527+00
\.


--
-- Data for Name: hospitals; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.hospitals (id, hospital_code, name, hospital_type, district, panchayat, address, phone, email, emergency_number, latitude, longitude, is_active, created_at, updated_at) FROM stdin;
46	HOSP001	Government Medical College Kottayam	Government Medical College	Kottayam	Gandhinagar	Medical College PO, Gandhinagar, Kottayam, Kerala 686008	+914812597284	gmckottayam@kerala.gov.in	108	9.6234	76.5387	t	2026-09-24 17:53:14.089125+00	2026-09-24 17:53:14.089129+00
47	HOSP002	General Hospital Ernakulam	Government General Hospital	Ernakulam	Kochi Corporation	Hospital Road, Marine Drive, Kochi, Ernakulam, Kerala 682011	+914842361251	ghosp.ekm@kerala.gov.in	108	9.9723	76.2812	t	2026-09-24 17:53:14.089131+00	2026-09-24 17:53:14.089131+00
48	HOSP003	Government Medical College Kozhikode	Government Medical College	Kozhikode	Kozhikode Corporation	17 Medical College Road, Kozhikode, Kerala 673008	+914952350216	gmckozhikode@kerala.gov.in	108	11.2721	75.8344	t	2026-09-24 17:53:14.089132+00	2026-09-24 17:53:14.089133+00
49	HOSP004	Government Medical College Thiruvananthapuram	Government Medical College	Thiruvananthapuram	Medical College	Medical College Junction, Thiruvananthapuram, Kerala 695011	+914712528300	gmctvm@kerala.gov.in	108	8.5241	76.9298	t	2026-09-24 17:53:14.089133+00	2026-09-24 17:53:14.089134+00
50	HOSP005	District Hospital Palakkad	District Hospital	Palakkad	Palakkad Municipality	Near Fort Maidan, Palakkad, Kerala 678001	+914912534522	dhpalakkad@kerala.gov.in	108	10.7753	76.6542	t	2026-09-24 17:53:14.089134+00	2026-09-24 17:53:14.089135+00
51	HOSP006	General Hospital Alappuzha	General Hospital	Alappuzha	Alappuzha Municipality	Iron Bridge Road, Alappuzha, Kerala 688001	+914772253324	ghalappuzha@kerala.gov.in	108	9.4981	76.3388	t	2026-09-24 17:53:14.089135+00	2026-09-24 17:53:14.089136+00
52	HOSP007	Government Medical College Thrissur	Government Medical College	Thrissur	Mulamkunnathukavu	Mulamkunnathukavu, Thrissur, Kerala 680596	+914872200310	gmcthrissur@kerala.gov.in	108	10.6092	76.2081	t	2026-09-24 17:53:14.089136+00	2026-09-24 17:53:14.089136+00
53	HOSP008	District Hospital Mananthavady	District Hospital	Wayanad	Mananthavady Municipality	Mananthavady, Wayanad, Kerala 670645	+914935240223	dhmananthavady@kerala.gov.in	108	11.8021	76.0034	t	2026-09-24 17:53:14.089137+00	2026-09-24 17:53:14.089137+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, user_code, hospital_id, email, hashed_password, full_name, phone_number, role, district, panchayat, is_active, last_login_at, created_at, updated_at) FROM stdin;
20	USR002	46	kottayam.admin@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$CiHkPIeQcs65l/L+X8s5xw$oHwBW+/M3MPvvMPRJtGBlLprYDLtgmRc5WvpdfMuBi0	Dr. Suresh Kumar (Blood Bank In-charge)	+919447000002	HOSPITAL_ADMIN	Kottayam	Gandhinagar	t	\N	2026-09-24 17:53:14.664631+00	2026-09-24 17:53:14.664632+00
21	USR003	46	kottayam.staff@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$IkTImRPCOAcAoLQ2BsCYcw$INULyJVten3P+tkXwS0sdfHNnAgSkq55mzS0nAxzO04	Rincy Varghese (Staff Nurse)	+919447000003	STAFF	Kottayam	Gandhinagar	t	\N	2026-09-24 17:53:14.664632+00	2026-09-24 17:53:14.664632+00
22	USR004	47	ekm.admin@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$q7UWghAixBjjHIOQ0lrLmQ$3nh0CG4OdgHLJatu90g1r/nrDKHj1bUsVRWWfrvVDW4	Dr. Lakshmi N (Medical Officer)	+919447000004	HOSPITAL_ADMIN	Ernakulam	Kochi	t	\N	2026-09-24 17:53:14.664633+00	2026-09-24 17:53:14.664634+00
23	USR005	48	calicut.admin@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$HcOYs7aWUqr1vhdijFHqXQ$1WNCCBb6kQq4yqsgP8NYL+0XjZ8WdwSHSryCacojM34	Dr. Abdul Rasheed (Blood Bank Head)	+919447000005	HOSPITAL_ADMIN	Kozhikode	Kozhikode	t	\N	2026-09-24 17:53:14.664634+00	2026-09-24 17:53:14.664634+00
24	USR006	49	tvm.admin@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$F4JQqlUKAUDofe89hzDGeA$0Ui8PWjvSUqGKXslAbiKd1jqO4UX6FlHI90fd2ty2Yw	Dr. Ananthakrishnan G	+919447000006	HOSPITAL_ADMIN	Thiruvananthapuram	Medical College	t	\N	2026-09-24 17:53:14.664635+00	2026-09-24 17:53:14.664635+00
19	USR001	\N	admin@rakthasethu.org	$argon2id$v=19$m=65536,t=3,p=4$DOEco/Qew/h/r/Ue41yLEQ$PfF5tXTW+lBu8IXMhHE6y1k/tEdLNfRh45tpsJGvUh4	State Super Admin	+919447000001	SUPER_ADMIN	Thiruvananthapuram	Secretariat	t	2026-09-25 09:55:18.256436+00	2026-09-24 17:53:14.664624+00	2026-09-25 09:55:18.257074+00
\.


--
-- Name: blood_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.blood_requests_id_seq', 65, true);


--
-- Name: donations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.donations_id_seq', 70, true);


--
-- Name: donor_import_batches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.donor_import_batches_id_seq', 60, true);


--
-- Name: donors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.donors_id_seq', 324, true);


--
-- Name: hospitals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.hospitals_id_seq', 53, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 24, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: blood_requests blood_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blood_requests
    ADD CONSTRAINT blood_requests_pkey PRIMARY KEY (id);


--
-- Name: donations donations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donations
    ADD CONSTRAINT donations_pkey PRIMARY KEY (id);


--
-- Name: donor_import_batches donor_import_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donor_import_batches
    ADD CONSTRAINT donor_import_batches_pkey PRIMARY KEY (id);


--
-- Name: donors donors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donors
    ADD CONSTRAINT donors_pkey PRIMARY KEY (id);


--
-- Name: hospitals hospitals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hospitals
    ADD CONSTRAINT hospitals_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_donations_date_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donations_date_status ON public.donations USING btree (donation_date, status);


--
-- Name: idx_donations_donor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donations_donor_id ON public.donations USING btree (donor_id);


--
-- Name: idx_donations_hospital_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donations_hospital_id ON public.donations USING btree (hospital_id);


--
-- Name: idx_donors_active_available; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donors_active_available ON public.donors USING btree (is_active, is_available);


--
-- Name: idx_donors_blood_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donors_blood_group ON public.donors USING btree (blood_group);


--
-- Name: idx_donors_district; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donors_district ON public.donors USING btree (district);


--
-- Name: idx_donors_matching_composite; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_donors_matching_composite ON public.donors USING btree (blood_group, district, is_active, is_available);


--
-- Name: idx_hospitals_district; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hospitals_district ON public.hospitals USING btree (district);


--
-- Name: idx_hospitals_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hospitals_is_active ON public.hospitals USING btree (is_active);


--
-- Name: idx_import_batches_hospital_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_import_batches_hospital_id ON public.donor_import_batches USING btree (hospital_id);


--
-- Name: idx_import_batches_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_import_batches_status ON public.donor_import_batches USING btree (status);


--
-- Name: idx_requests_blood_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_requests_blood_group ON public.blood_requests USING btree (blood_group);


--
-- Name: idx_requests_district; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_requests_district ON public.blood_requests USING btree (district);


--
-- Name: idx_requests_hospital_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_requests_hospital_id ON public.blood_requests USING btree (hospital_id);


--
-- Name: idx_requests_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_requests_status ON public.blood_requests USING btree (status);


--
-- Name: idx_requests_urgency; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_requests_urgency ON public.blood_requests USING btree (urgency);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_hospital_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_hospital_id ON public.users USING btree (hospital_id);


--
-- Name: ix_blood_requests_request_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_blood_requests_request_code ON public.blood_requests USING btree (request_code);


--
-- Name: ix_donations_donation_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_donations_donation_code ON public.donations USING btree (donation_code);


--
-- Name: ix_donations_donation_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_donations_donation_date ON public.donations USING btree (donation_date);


--
-- Name: ix_donor_import_batches_batch_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_donor_import_batches_batch_code ON public.donor_import_batches USING btree (batch_code);


--
-- Name: ix_donors_donor_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_donors_donor_code ON public.donors USING btree (donor_code);


--
-- Name: ix_donors_full_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_donors_full_name ON public.donors USING btree (full_name);


--
-- Name: ix_donors_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_donors_phone ON public.donors USING btree (phone);


--
-- Name: ix_hospitals_hospital_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_hospitals_hospital_code ON public.hospitals USING btree (hospital_code);


--
-- Name: ix_hospitals_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_hospitals_name ON public.hospitals USING btree (name);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_user_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_user_code ON public.users USING btree (user_code);


--
-- Name: blood_requests blood_requests_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blood_requests
    ADD CONSTRAINT blood_requests_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id) ON DELETE RESTRICT;


--
-- Name: donations donations_donor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donations
    ADD CONSTRAINT donations_donor_id_fkey FOREIGN KEY (donor_id) REFERENCES public.donors(id) ON DELETE RESTRICT;


--
-- Name: donations donations_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donations
    ADD CONSTRAINT donations_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id) ON DELETE SET NULL;


--
-- Name: donor_import_batches donor_import_batches_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donor_import_batches
    ADD CONSTRAINT donor_import_batches_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id) ON DELETE SET NULL;


--
-- Name: donor_import_batches donor_import_batches_uploaded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donor_import_batches
    ADD CONSTRAINT donor_import_batches_uploaded_by_user_id_fkey FOREIGN KEY (uploaded_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: donors donors_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.donors
    ADD CONSTRAINT donors_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id) ON DELETE SET NULL;


--
-- Name: users users_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict lLVjJsTJYMDoAo9rFFyRjiFUdfkkcksEbsO9s5HAqdmVWCFsYOtYhTkrlNpubZt

