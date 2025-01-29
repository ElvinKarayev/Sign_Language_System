--
-- PostgreSQL database dump
--

-- Dumped from database version 16.6 (Ubuntu 16.6-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.6 (Ubuntu 16.6-0ubuntu0.24.04.1)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: sentences; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sentences (
    sentence_id integer NOT NULL,
    sentence_language character varying(50),
    sentence_content text,
    user_id integer
);


ALTER TABLE public.sentences OWNER TO postgres;

--
-- Name: sentences_sentence_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sentences_sentence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sentences_sentence_id_seq OWNER TO postgres;

--
-- Name: sentences_sentence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sentences_sentence_id_seq OWNED BY public.sentences.sentence_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(100) NOT NULL,
    country character varying(100),
    user_role character varying(50),
    consent_status boolean,
    telegram_id bigint
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: videos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.videos (
    video_id integer NOT NULL,
    text_id integer,
    video_reference_id integer,
    user_id integer,
    positive_scores integer,
    negative_scores integer,
    language character varying(40) NOT NULL,
    file_path text,
    uploaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.videos OWNER TO postgres;

--
-- Name: videos_video_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.videos_video_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.videos_video_id_seq OWNER TO postgres;

--
-- Name: videos_video_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.videos_video_id_seq OWNED BY public.videos.video_id;


--
-- Name: votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.votes (
    vote_id integer NOT NULL,
    user_id integer,
    video_id integer,
    vote_type character varying(10),
    vote_timestamp timestamp without time zone
);


ALTER TABLE public.votes OWNER TO postgres;

--
-- Name: votes_vote_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.votes_vote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.votes_vote_id_seq OWNER TO postgres;

--
-- Name: votes_vote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.votes_vote_id_seq OWNED BY public.votes.vote_id;


--
-- Name: sentences sentence_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sentences ALTER COLUMN sentence_id SET DEFAULT nextval('public.sentences_sentence_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: videos video_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos ALTER COLUMN video_id SET DEFAULT nextval('public.videos_video_id_seq'::regclass);


--
-- Name: votes vote_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes ALTER COLUMN vote_id SET DEFAULT nextval('public.votes_vote_id_seq'::regclass);


--
-- Data for Name: sentences; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.sentences (sentence_id, sentence_language, sentence_content, user_id) FROM stdin;
1	Azerbaijani	Hamıya salam. Mən xüsusi məktəbdə işləyirəm.	2
2	Azerbaijani	Məktəbimizdə zəifeşidən və eşitməsi tamamilə məhdud olan uşaqlar təhsil alır.	2
6	Azerbaijani	Indi bir az işim var	7
7	Azerbaijani	Məndə problem yoxdur	7
8	Azerbaijani	Sabah axşam görüşə bilərikmi?	7
9	Azerbaijani	Bu gün mən az yatmışam	7
10	Azerbaijani	Bu gün vacib iclasım var	7
11	Azerbaijani	Hamı deyir ki işarət dilini öyrənmək çox çətindir amma yox asandır.	2
12	Azerbaijani	Eşitmə məhdudiyyətli uşaqlar tikməyi bacarır, toxumağı bacarır, rəsm çəkməyi bacarır	2
13	Azerbaijani	Sırağagün axşam çoxlu yağış yağdı amma səhər gün çıxdı. (Günəş var idi)	2
14	Azerbaijani	Mənim 2 oğlum var	7
15	Azerbaijani	Mənim qara pişiyim var	7
16	Azerbaijani	Mən rus dilini bilirəm	7
17	Azerbaijani	Mən Bakıda yaşayıram	7
18	Azerbaijani	Sizə indi kömək lazımdır?	7
19	Azerbaijani	Mən sabah saat 2də səni Gənclik metrosunda gözləyəcəm.	7
20	Azerbaijani	Mənim sabah 2 nəfərlə online görüşüm olacaq	7
48	Azerbaijani	Salam, dəyərli dostlar !	13
49	Azerbaijani	Mənim 24 yaşım var	13
50	Azerbaijani	İşarə dili çox mürəkkəb və həmçinin çox maraqlıdır	13
51	Azerbaijani	Sənin neçə yaşın var?	13
54	Azerbaijani	Test	12
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, username, country, user_role, consent_status, telegram_id) FROM stdin;
1	unknown	Azerbaijani	Translator	t	836876907
2	unknown	Azerbaijani	Translator	t	331202815
6	aliyeffa2oo4	Azerbaijani	User	t	1481278646
7	jhasanov	Azerbaijani	Translator	t	444371463
9	SamaMustafazade	Azerbaijani	User	t	1177752681
10	Shamil_sabir	Azerbaijani	Translator	t	943424004
8	HSTechk	Azerbaijani	User	t	1323792586
12	gultajj	Azerbaijani	Translator	t	612594692
13	HeydarRahimli	Azerbaijani	Translator	t	1079279364
14	unknown	Azerbaijani	User	t	5449479946
15	OrkhanIb	Azerbaijani	User	t	976422791
16	unknown	Azerbaijani	User	t	1933790365
17	Nargiz_Najafzada	Azerbaijani	User	t	767768390
18	unknown	Azerbaijani	User	t	1013113153
19	unknown	Azerbaijani	User	t	6985998082
20	X67926	Azerbaijani	User	t	1948072824
21	Pnhli	Azerbaijani	User	t	6849085694
22	unknown	Azerbaijani	User	t	1253043279
23	Eytieleysi	Azerbaijani	User	t	786916031
24	unknown	Azerbaijani	User	t	6020373839
25	unknown	Azerbaijani	User	t	5469682143
26	qshirinova	Azerbaijani	User	t	910075890
27	narmmva	Azerbaijani	User	t	1282821729
28	OneAK8	Azerbaijani	User	t	988254131
29	unknown	Azerbaijani	User	t	2133203039
30	unknown	Azerbaijani	User	t	1583558517
31	mu7adov	Azerbaijani	User	t	961292343
32	orxan_m_57	Azerbaijani	User	t	5728849149
33	unknown	Azerbaijani	User	t	6688642466
34	unknown	Azerbaijani	User	t	7850092630
35	jeylanamiraliyeva	Azerbaijani	User	t	7379822363
36	unknown	Azerbaijani	User	t	6676514735
37	esmer_97	Azerbaijani	User	t	1165399708
38	Narmin664	Azerbaijani	User	t	1093960394
39	unknown	Azerbaijani	User	t	1182453604
40	unknown	Azerbaijani	User	t	1953464519
41	gulagha_026	Azerbaijani	User	t	1857772918
42	unknown	Azerbaijani	User	t	6234653624
43	unknown	Azerbaijani	User	t	7083991721
44	unknown	Azerbaijani	User	t	6723350971
45	innosevda	Azerbaijani	User	t	1346391792
\.


--
-- Data for Name: videos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.videos (video_id, text_id, video_reference_id, user_id, positive_scores, negative_scores, language, file_path, uploaded_at) FROM stdin;
11	8	8	9	\N	2	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_9_SamaMustafazade_1.mp4	2025-01-23 22:13:24.153471
16	7	7	8	3	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_1.mp4	2025-01-23 22:46:33.537797
17	10	10	8	2	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_2.mp4	2025-01-23 22:48:24.926118
20	9	9	8	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_5.mp4	2025-01-23 22:56:40.448864
13	6	6	9	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_9_SamaMustafazade_3.mp4	2025-01-23 22:18:56.524347
12	9	9	9	1	2	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_9_SamaMustafazade_2.mp4	2025-01-23 22:16:46.174583
14	10	10	9	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_9_SamaMustafazade_4.mp4	2025-01-23 22:20:07.319696
15	7	7	9	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_9_SamaMustafazade_5.mp4	2025-01-23 22:23:40.460519
19	6	6	8	1	2	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_4.mp4	2025-01-23 22:54:45.578587
18	8	8	8	\N	2	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_3.mp4	2025-01-23 22:51:33.699303
23	13	\N	2	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_2_unknown_5.mp4	2025-01-24 09:12:55.766322
8	8	\N	7	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_3.mp4	2025-01-22 14:40:27.591234
1	1	\N	2	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_2_unknown_1.mp4	2025-01-16 10:54:29.71355
6	6	\N	7	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_1.mp4	2025-01-22 14:38:08.216775
2	2	\N	2	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_2_unknown_2.mp4	2025-01-17 04:58:04.855293
10	10	\N	7	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_5.mp4	2025-01-22 14:44:18.88855
7	7	\N	7	3	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_2.mp4	2025-01-22 14:39:04.909721
59	49	\N	13	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_13_HeydarRahimli_2.mp4	2025-01-27 10:04:28.869565
24	14	\N	7	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_6.mp4	2025-01-25 12:21:16.183356
21	11	\N	2	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_2_unknown_3.mp4	2025-01-24 09:10:16.717617
22	12	\N	2	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_2_unknown_4.mp4	2025-01-24 09:11:18.862438
9	9	\N	7	3	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_4.mp4	2025-01-22 14:42:30.505376
61	51	\N	13	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_13_HeydarRahimli_4.mp4	2025-01-27 10:07:56.87519
28	18	\N	7	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_10.mp4	2025-01-25 12:28:57.955706
26	16	\N	7	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_8.mp4	2025-01-25 12:24:45.089977
29	19	\N	7	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_11.mp4	2025-01-26 11:00:56.723872
60	50	\N	13	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_13_HeydarRahimli_3.mp4	2025-01-27 10:06:12.596681
58	48	\N	13	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_13_HeydarRahimli_1.mp4	2025-01-27 10:02:52.561793
27	17	\N	7	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_9.mp4	2025-01-25 12:25:33.628504
25	15	\N	7	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_7.mp4	2025-01-25 12:23:29.052293
30	20	\N	7	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_7_jhasanov_12.mp4	2025-01-26 11:04:24.46588
67	18	28	8	2	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_9.mp4	2025-01-28 01:16:35.459605
69	14	24	8	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_11.mp4	2025-01-28 01:24:36.929306
64	48	58	8	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_6.mp4	2025-01-28 01:08:32.046204
71	16	26	8	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_13.mp4	2025-01-28 01:27:59.082258
70	51	61	8	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_12.mp4	2025-01-28 01:26:34.544398
72	19	29	8	1	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_14.mp4	2025-01-28 01:31:47.773659
73	20	30	8	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_15.mp4	2025-01-28 01:34:46.811029
65	17	27	8	\N	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_7.mp4	2025-01-28 01:10:10.698948
68	1	1	8	1	1	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_10.mp4	2025-01-28 01:22:20.80542
66	15	25	8	\N	2	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/User/user_video_8_HSTechk_8.mp4	2025-01-28 01:13:51.039626
76	54	\N	12	\N	\N	Azerbaijani	/home/ubuntu/Sign_Language_System/Video/Translator/translator_video_12_gultajj_1.mp4	2025-01-29 09:46:47.530323
\.


--
-- Data for Name: votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.votes (vote_id, user_id, video_id, vote_type, vote_timestamp) FROM stdin;
1	7	2	up	2025-01-22 14:46:02.937414
2	7	1	up	2025-01-22 14:46:12.38379
3	2	10	up	2025-01-23 20:07:53.178217
4	2	6	up	2025-01-23 20:08:53.566586
5	2	9	up	2025-01-23 20:09:00.893671
6	2	8	up	2025-01-23 20:09:18.308721
7	2	7	up	2025-01-23 20:09:27.376129
8	10	9	up	2025-01-23 20:24:24.454486
9	10	8	down	2025-01-23 20:24:46.52326
10	10	1	up	2025-01-23 20:24:58.711083
11	10	6	up	2025-01-23 20:25:09.202311
12	10	2	down	2025-01-23 20:25:37.258424
13	10	7	up	2025-01-23 20:25:46.639158
14	10	10	down	2025-01-23 20:26:15.747802
15	7	17	up	2025-01-24 07:12:31.000035
16	7	13	down	2025-01-24 07:12:47.405064
17	7	19	down	2025-01-24 07:12:58.189115
18	7	14	down	2025-01-24 07:13:07.97864
19	7	15	up	2025-01-25 12:17:56.50966
20	7	21	up	2025-01-25 12:18:12.770271
21	7	12	down	2025-01-25 12:18:20.59906
22	7	22	up	2025-01-25 12:18:47.046378
23	7	16	up	2025-01-25 12:18:55.48264
24	7	20	down	2025-01-25 12:19:03.484683
25	7	18	down	2025-01-25 12:19:13.125191
26	7	23	up	2025-01-25 12:19:26.249743
27	7	11	down	2025-01-25 12:19:34.8574
28	13	28	up	2025-01-27 09:29:54.330175
29	13	16	up	2025-01-27 09:30:18.385198
30	13	17	down	2025-01-27 09:30:28.549294
31	13	26	up	2025-01-27 09:31:30.537737
32	13	12	down	2025-01-27 09:31:53.898098
33	13	7	up	2025-01-27 09:31:59.232549
34	13	19	down	2025-01-27 09:32:06.091809
35	13	9	up	2025-01-27 09:32:24.229687
36	7	59	up	2025-01-27 11:07:37.283185
37	7	60	up	2025-01-27 11:07:47.768662
38	7	58	up	2025-01-27 11:08:02.704908
39	7	61	up	2025-01-27 11:08:13.905105
40	2	26	up	2025-01-27 19:18:19.65934
41	2	29	down	2025-01-27 19:18:34.568079
42	2	12	up	2025-01-27 19:18:42.104215
43	2	60	up	2025-01-27 19:18:51.324082
44	2	24	up	2025-01-27 19:18:59.669591
45	2	58	up	2025-01-27 19:19:06.494925
46	2	14	up	2025-01-27 19:19:16.651867
47	2	15	up	2025-01-27 19:19:23.396419
48	2	11	down	2025-01-27 19:19:31.729181
49	2	16	up	2025-01-27 19:19:38.951583
50	2	59	up	2025-01-27 19:19:46.470199
51	13	24	up	2025-01-27 19:19:47.555158
52	2	17	up	2025-01-27 19:19:54.189637
53	2	20	up	2025-01-27 19:20:00.608566
54	2	13	up	2025-01-27 19:20:09.094617
55	2	61	up	2025-01-27 19:20:20.295318
56	2	28	up	2025-01-27 19:20:28.161033
57	2	27	up	2025-01-27 19:20:34.749934
58	2	19	up	2025-01-27 19:20:43.280266
59	2	18	down	2025-01-27 19:20:50.470884
60	2	25	down	2025-01-27 19:21:02.399856
61	2	30	up	2025-01-27 19:21:13.139013
63	7	69	down	2025-01-28 07:04:30.244086
64	7	64	up	2025-01-28 07:04:38.530449
65	7	71	down	2025-01-28 07:04:47.502319
66	7	70	up	2025-01-28 07:05:03.778717
67	7	72	up	2025-01-28 07:05:20.642835
68	7	73	down	2025-01-28 07:05:57.799855
69	7	68	up	2025-01-28 07:06:15.551499
70	7	66	down	2025-01-28 07:06:24.609841
71	7	67	up	2025-01-28 07:06:39.067318
72	7	65	down	2025-01-28 07:06:50.09173
73	2	67	up	2025-01-28 18:26:06.807183
75	2	68	down	2025-01-28 18:26:26.581801
76	2	66	down	2025-01-28 18:26:34.745454
\.


--
-- Name: sentences_sentence_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.sentences_sentence_id_seq', 54, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 45, true);


--
-- Name: videos_video_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.videos_video_id_seq', 76, true);


--
-- Name: votes_vote_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.votes_vote_id_seq', 76, true);


--
-- Name: sentences sentences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sentences
    ADD CONSTRAINT sentences_pkey PRIMARY KEY (sentence_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_telegram_id_key UNIQUE (telegram_id);


--
-- Name: videos videos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_pkey PRIMARY KEY (video_id);


--
-- Name: votes votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_pkey PRIMARY KEY (vote_id);


--
-- Name: votes fk_video; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT fk_video FOREIGN KEY (video_id) REFERENCES public.videos(video_id) ON DELETE CASCADE;


--
-- Name: videos user_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT user_id_fk FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: sentences user_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sentences
    ADD CONSTRAINT user_id_fk FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: videos videos_text_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_text_id_fkey FOREIGN KEY (text_id) REFERENCES public.sentences(sentence_id) ON DELETE CASCADE;


--
-- Name: votes votes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- PostgreSQL database dump complete
--

