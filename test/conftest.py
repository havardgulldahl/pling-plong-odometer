import pytest

@pytest.fixture(scope='session', autouse=True)
def xmemlfiles(request):
    DMA = {"NONRO716733SG0201": "NONRO716733SG0201 Ofelastema.wav",
           "NONRO174537CD0001": "NONRO174537CD0001 Klaverkonsert, op. 16, a-moll_ 1. sats. Alleg.wav",
           "NONRE643326HD0001": "NONRE643326HD0001 Panda.wav",
           "NONRO306374CS0002": "NONRO306374CS0002 Phone Tap (Instrumental).wav",
           "NONRE643326LP0001": "NONRE643326LP0001 Panda.wav",}

    AUX = {"SCD086738": "SCD086738_PRETTY IN PINK_SONOTON.wav",
           "SCD074002": "AUXMP_SCD074002_HEARTWARMING  B.wav",
           "RSM010436": "AUXMP_RSM010436_HEAVY URBAN.mp3",
           "UBMM214809": "AUXMP_UBMM214809_EVIL FORCES.wav"}


    APOLLO = {"MUM_124_17": "Apollo_MUM_124_17__Trail_Rider__Donnelly,_Steve.mp3",
              "DWCD_514_3": "Apollo_DWCD_514_3__Big_Game_Hunter__Sir_Bald_Diddley.mp3",
              "NVS_102_27": "Apollo_NVS_102_27__Unyielding__Dan_Elias_Brevig.mp3",
              "SL_60_37": "Apollo_SL_60_37__Hey_Mack_(rhythm_section)__Matthew_David_Waldrum.mp3"}

    UPRIGHT = {"EDS_016_006": "_UPRIGHT_EDS_016_006_Downplay_(Main).WAV",
               "EDS_016_011": "_UPRIGHT_EDS_016_011_Jagged_Edge_(Main).WAV",
               "EDS_016_011": "_UPRIGHT_EDS_016_011_Jagged_Edge_(Main).MP3"}


    UNIPPM = {"777051": "KOK_2360_32_Lightning_Drone_Chevalier_777051",
              "627163": "KOS_97_11_Rap_And_Scratch_Andreasen_Kalfayan_627163.wav",
              "714159": "RNM_50_9_You_Ives_714159.wav",
              "863434": "VTMA_26_33_Lonely_Traveller_863434.wav",
              "25175": "EDGE_21_63_Slow_Downer_Cunningham_Fox_Lang_25175.wav",
              "896746": "STSC_77_14_A_Million_Copeland_Darnell_Desmond_Kalayeh_896746.wav",
              "762667": "STFTA_1_175_Don_t_Take_Me_Down_Hart_Williams_762667.wav",
              "858425": "BR_586_5_Unstoppable_Force_Britton_858425.wav",
              "652177": "CHAP_386_2_Neapolitan_Love_Song_Stott_652177.wav",
              "897593": "RDR_18_5_Sunshine_Shapes_Instrumental_Keane_897593.wav",
              "898428": "BER_1250_89_Stress_mit_Recht_Muller_898428.wav",
              "66126": "CHAPWR_6_4_Sufi_Hamadcha_Amar_66126.wav",
              "920961": "SUN_3_2_Neon_Pulse_Keaton_Thomas_920961.wav",
              "321775": "LO_CD_18_6_East_Of_West_Black_Carpenter_More_321775.wav",
              "762667": "STFTA_1_175_Don_t_Take_Me_Down_Hart_Williams_762667.wav",
              "912768": "SOHO_153_6_Liquor_To_Pandas_Ghettososcks_Lamb_Ross_912768.wav",


              }

    EXTREME = {"SCS069_02": "SCS069_02 MR DARKSIDE.WAV",
               "SCS062_06_3": "SCS062_06_3 DINGO BINGO_DIDGERIDOO ONLY.WAV",
               }


    return {'DMA': DMA,
            'AUX': AUX,
            'APOLLO': APOLLO,
            'UPRIGHT': UPRIGHT,
            'UNIPPM': UNIPPM,
            'EXTREME': EXTREME,
            }
