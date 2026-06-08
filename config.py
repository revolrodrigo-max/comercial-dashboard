TRIAGE_SHEET_ID = "1PRJ18j3IQOn2NSEzKzzd7QlCJriqn2K2BK4T2VPEgto"
CLOSER_SHEET_ID = "1QHYMMjEHnH8_6vJua20vMDy5-dnNGb3iX5io_t5n7ns"
CACHE_TTL = 300  # seconds

FUNNEL_STAGES = ["Agendados", "Asistieron", "Calificaron", "Compraron"]

# Brand palette
BRAND_GREEN  = "#C7FF00"
BRAND_BLACK  = "#000000"
BRAND_WHITE  = "#FFFFFF"
BRAND_GREY   = "#6B6969"
BRAND_GREY2  = "#3A3A3A"   # darker grey for secondary backgrounds
BRAND_GREEN2 = "#9ECC00"   # slightly darker green for contrast

CLOSER_COLORS = {
    "Santi Capurro": BRAND_GREEN,
    "Santi Correa":  BRAND_WHITE,
    "Gianluca":      BRAND_GREY,
    "Santiago":      BRAND_GREEN2,
    "Joaquin":       "#E0E0E0",
    "Rodrigo":       "#4A4A4A",
}

PAYMENT_COLORS = {
    "PIFF":        BRAND_GREEN,
    "CUOTAS":      BRAND_WHITE,
    "Retroactivo": BRAND_GREY,
    "UPSELL":      BRAND_GREEN2,
}

# Sequential scale for charts (dark → brand green)
BRAND_SCALE = ["#1A1A1A", "#3A3A3A", BRAND_GREY, BRAND_GREEN2, BRAND_GREEN]
