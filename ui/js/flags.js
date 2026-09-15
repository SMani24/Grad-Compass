/**
 * Global Flag & Country Resolver for Grad Compass
 * Maps countries by both normalized name and ISO 3166-1 alpha-3 code.
 */

const WORLD_COUNTRIES = [
  { code: "AFG", name: "Afghanistan", flag: "🇦🇫" },
  { code: "ALB", name: "Albania", flag: "🇦🇱" },
  { code: "DZA", name: "Algeria", flag: "🇩🇿" },
  { code: "AND", name: "Andorra", flag: "🇦🇩" },
  { code: "AGO", name: "Angola", flag: "🇦🇴" },
  { code: "ATG", name: "Antigua and Barbuda", flag: "🇦🇬", aliases: ["antigua and barb"] },
  { code: "ARG", name: "Argentina", flag: "🇦🇷" },
  { code: "ARM", name: "Armenia", flag: "🇦🇲" },
  { code: "AUS", name: "Australia", flag: "🇦🇺" },
  { code: "AUT", name: "Austria", flag: "🇦🇹" },
  { code: "AZE", name: "Azerbaijan", flag: "🇦🇿" },
  { code: "BHS", name: "Bahamas", flag: "🇧🇸", aliases: ["the bahamas"] },
  { code: "BHR", name: "Bahrain", flag: "🇧🇭" },
  { code: "BGD", name: "Bangladesh", flag: "🇧🇩" },
  { code: "BRB", name: "Barbados", flag: "🇧🇧" },
  { code: "BLR", name: "Belarus", flag: "🇧🇾" },
  { code: "BEL", name: "Belgium", flag: "🇧🇪" },
  { code: "BLZ", name: "Belize", flag: "🇧🇿" },
  { code: "BEN", name: "Benin", flag: "🇧🇯" },
  { code: "BTN", name: "Bhutan", flag: "🇧🇹" },
  { code: "BOL", name: "Bolivia", flag: "🇧🇴" },
  { code: "BIH", name: "Bosnia and Herzegovina", flag: "🇧🇦", aliases: ["bosnia and herz"] },
  { code: "BWA", name: "Botswana", flag: "🇧🇼" },
  { code: "BRA", name: "Brazil", flag: "🇧🇷" },
  { code: "BRN", name: "Brunei", flag: "🇧🇳" },
  { code: "BGR", name: "Bulgaria", flag: "🇧🇬" },
  { code: "BFA", name: "Burkina Faso", flag: "🇧🇫" },
  { code: "BDI", name: "Burundi", flag: "🇧🇮" },
  { code: "KHM", name: "Cambodia", flag: "🇰🇭" },
  { code: "CMR", name: "Cameroon", flag: "🇨🇲" },
  { code: "CAN", name: "Canada", flag: "🇨🇦" },
  { code: "CPV", name: "Cape Verde", flag: "🇨🇻", aliases: ["cabo verde"] },
  { code: "CAF", name: "Central African Republic", flag: "🇨🇫", aliases: ["central african rep"] },
  { code: "TCD", name: "Chad", flag: "🇹🇩" },
  { code: "CHL", name: "Chile", flag: "🇨🇱" },
  { code: "CHN", name: "China", flag: "🇨🇳" },
  { code: "COL", name: "Colombia", flag: "🇨🇴" },
  { code: "COM", name: "Comoros", flag: "🇰🇲" },
  { code: "COG", name: "Congo", flag: "🇨🇬", aliases: ["rep congo", "republic of the congo"] },
  { code: "COD", name: "Democratic Republic of the Congo", flag: "🇨🇩", aliases: ["dem rep congo", "drc"] },
  { code: "CRI", name: "Costa Rica", flag: "🇨🇷" },
  { code: "CIV", name: "Ivory Coast", flag: "🇨🇮", aliases: ["cote d ivoire", "cote d'ivoire"] },
  { code: "HRV", name: "Croatia", flag: "🇭🇷" },
  { code: "CUB", name: "Cuba", flag: "🇨🇺" },
  { code: "CYP", name: "Cyprus", flag: "🇨🇾", aliases: ["n cyprus", "northern cyprus"] },
  { code: "CZE", name: "Czech Republic", flag: "🇨🇿", aliases: ["czechia"] },
  { code: "DNK", name: "Denmark", flag: "🇩🇰" },
  { code: "DJI", name: "Djibouti", flag: "🇩🇯" },
  { code: "DOM", name: "Dominican Republic", flag: "🇩🇴", aliases: ["dominican rep"] },
  { code: "ECU", name: "Ecuador", flag: "🇪🇨" },
  { code: "EGY", name: "Egypt", flag: "🇪🇬" },
  { code: "SLV", name: "El Salvador", flag: "🇸🇻" },
  { code: "GNQ", name: "Equatorial Guinea", flag: "🇬🇶", aliases: ["eq guinea"] },
  { code: "ERI", name: "Eritrea", flag: "🇪🇷" },
  { code: "EST", name: "Estonia", flag: "🇪🇪" },
  { code: "SWZ", name: "Eswatini", flag: "🇸🇿", aliases: ["swaziland"] },
  { code: "ETH", name: "Ethiopia", flag: "🇪🇹" },
  { code: "FJI", name: "Fiji", flag: "🇫🇯" },
  { code: "FIN", name: "Finland", flag: "🇫🇮" },
  { code: "FRA", name: "France", flag: "🇫🇷" },
  { code: "GAB", name: "Gabon", flag: "🇬🇦" },
  { code: "GMB", name: "Gambia", flag: "🇬🇲", aliases: ["the gambia"] },
  { code: "GEO", name: "Georgia", flag: "🇬🇪" },
  { code: "DEU", name: "Germany", flag: "🇩🇪" },
  { code: "GHA", name: "Ghana", flag: "🇬🇭" },
  { code: "GRC", name: "Greece", flag: "🇬🇷" },
  { code: "GRL", name: "Greenland", flag: "🇬🇱" },
  { code: "GTM", name: "Guatemala", flag: "🇬🇹" },
  { code: "GIN", name: "Guinea", flag: "🇬🇮" },
  { code: "GNB", name: "Guinea-Bissau", flag: "🇬🇼" },
  { code: "GUY", name: "Guyana", flag: "🇬🇾" },
  { code: "HTI", name: "Haiti", flag: "🇭🇹" },
  { code: "HND", name: "Honduras", flag: "🇭🇳" },
  { code: "HKG", name: "Hong Kong", flag: "🇭🇰" },
  { code: "HUN", name: "Hungary", flag: "🇭🇺" },
  { code: "ISL", name: "Iceland", flag: "🇮🇸" },
  { code: "IND", name: "India", flag: "🇮🇳" },
  { code: "IDN", name: "Indonesia", flag: "🇮🇩" },
  { code: "IRN", name: "Iran", flag: "🇮🇷", aliases: ["islamic republic of iran"] },
  { code: "IRQ", name: "Iraq", flag: "🇮🇶" },
  { code: "IRL", name: "Ireland", flag: "🇮🇪" },
  { code: "ISR", name: "Israel", flag: "🇮🇱" },
  { code: "ITA", name: "Italy", flag: "🇮🇹" },
  { code: "JAM", name: "Jamaica", flag: "🇯🇲" },
  { code: "JPN", name: "Japan", flag: "🇯🇵" },
  { code: "JOR", name: "Jordan", flag: "🇯🇴" },
  { code: "KAZ", name: "Kazakhstan", flag: "🇰🇿" },
  { code: "KEN", name: "Kenya", flag: "🇰🇪" },
  { code: "XKX", name: "Kosovo", flag: "🇽🇰" },
  { code: "KWT", name: "Kuwait", flag: "🇰🇼" },
  { code: "KGZ", name: "Kyrgyzstan", flag: "🇰🇬" },
  { code: "LAO", name: "Laos", flag: "🇱🇦" },
  { code: "LVA", name: "Latvia", flag: "🇱🇻" },
  { code: "LBN", name: "Lebanon", flag: "🇱🇧" },
  { code: "LSO", name: "Lesotho", flag: "🇱🇸" },
  { code: "LBR", name: "Liberia", flag: "🇱🇷" },
  { code: "LBY", name: "Libya", flag: "🇱🇾" },
  { code: "LTU", name: "Lithuania", flag: "🇱🇹" },
  { code: "LUX", name: "Luxembourg", flag: "🇱🇺" },
  { code: "MDG", name: "Madagascar", flag: "🇲🇬" },
  { code: "MWI", name: "Malawi", flag: "🇲🇼" },
  { code: "MYS", name: "Malaysia", flag: "🇲🇾" },
  { code: "MLI", name: "Mali", flag: "🇲🇱" },
  { code: "MLT", name: "Malta", flag: "🇲🇹" },
  { code: "MRT", name: "Mauritania", flag: "🇲🇷" },
  { code: "MUS", name: "Mauritius", flag: "🇲🇺" },
  { code: "MEX", name: "Mexico", flag: "🇲🇽" },
  { code: "MDA", name: "Moldova", flag: "🇲🇩" },
  { code: "MNG", name: "Mongolia", flag: "🇲🇳" },
  { code: "MNE", name: "Montenegro", flag: "🇲🇪" },
  { code: "MAR", name: "Morocco", flag: "🇲🇦", aliases: ["w sahara", "western sahara"] },
  { code: "MOZ", name: "Mozambique", flag: "🇲🇿" },
  { code: "MMR", name: "Myanmar", flag: "🇲🇲", aliases: ["burma"] },
  { code: "NAM", name: "Namibia", flag: "🇳🇦" },
  { code: "NPL", name: "Nepal", flag: "🇳🇵" },
  { code: "NLD", name: "Netherlands", flag: "🇳🇱" },
  { code: "NZL", name: "New Zealand", flag: "🇳🇿" },
  { code: "NIC", name: "Nicaragua", flag: "🇳🇮" },
  { code: "NER", name: "Niger", flag: "🇳🇪" },
  { code: "NGA", name: "Nigeria", flag: "🇳🇬" },
  { code: "PRK", name: "North Korea", flag: "🇰🇵", aliases: ["dem rep korea"] },
  { code: "MKD", name: "North Macedonia", flag: "🇲🇰", aliases: ["macedonia"] },
  { code: "NOR", name: "Norway", flag: "🇳🇴" },
  { code: "OMN", name: "Oman", flag: "🇴🇲" },
  { code: "PAK", name: "Pakistan", flag: "🇵🇰" },
  { code: "PSE", name: "Palestine", flag: "🇵🇸" },
  { code: "PAN", name: "Panama", flag: "🇵🇦" },
  { code: "PNG", name: "Papua New Guinea", flag: "🇵🇬" },
  { code: "PRY", name: "Paraguay", flag: "🇵🇾" },
  { code: "PER", name: "Peru", flag: "🇵🇪" },
  { code: "PHL", name: "Philippines", flag: "🇵🇭" },
  { code: "POL", name: "Poland", flag: "🇵🇱" },
  { code: "PRT", name: "Portugal", flag: "🇵🇹" },
  { code: "PRI", name: "Puerto Rico", flag: "🇵🇷" },
  { code: "QAT", name: "Qatar", flag: "🇶🇦" },
  { code: "ROU", name: "Romania", flag: "🇷🇴" },
  { code: "RUS", name: "Russia", flag: "🇷🇺", aliases: ["russian federation"] },
  { code: "RWA", name: "Rwanda", flag: "🇷🇼" },
  { code: "SAU", name: "Saudi Arabia", flag: "🇸🇦" },
  { code: "SEN", name: "Senegal", flag: "🇸🇳" },
  { code: "SRB", name: "Serbia", flag: "🇷🇸" },
  { code: "SLE", name: "Sierra Leone", flag: "🇸🇱" },
  { code: "SGP", name: "Singapore", flag: "🇸🇬" },
  { code: "SVK", name: "Slovakia", flag: "🇸🇰" },
  { code: "SVN", name: "Slovenia", flag: "🇸🇮" },
  { code: "SLB", name: "Solomon Islands", flag: "🇸🇧", aliases: ["solomon is"] },
  { code: "SOM", name: "Somalia", flag: "🇸🇴", aliases: ["somaliland"] },
  { code: "ZAF", name: "South Africa", flag: "🇿🇦" },
  { code: "KOR", name: "South Korea", flag: "🇰🇷", aliases: ["korea", "republic of korea"] },
  { code: "SSD", name: "South Sudan", flag: "🇸🇸", aliases: ["s sudan"] },
  { code: "ESP", name: "Spain", flag: "🇪🇸" },
  { code: "LKA", name: "Sri Lanka", flag: "🇱🇰" },
  { code: "SDN", name: "Sudan", flag: "🇸🇩" },
  { code: "SUR", name: "Suriname", flag: "🇸🇷" },
  { code: "SWE", name: "Sweden", flag: "🇸🇪" },
  { code: "CHE", name: "Switzerland", flag: "🇨🇭" },
  { code: "SYR", name: "Syria", flag: "🇸🇾" },
  { code: "TWN", name: "Taiwan", flag: "🇹🇼" },
  { code: "TJK", name: "Tajikistan", flag: "🇹🇯" },
  { code: "TZA", name: "Tanzania", flag: "🇹🇿" },
  { code: "THA", name: "Thailand", flag: "🇹🇭" },
  { code: "TLS", name: "Timor-Leste", flag: "🇹🇱" },
  { code: "TGO", name: "Togo", flag: "🇹🇬" },
  { code: "TTO", name: "Trinidad and Tobago", flag: "🇹🇹" },
  { code: "TUN", name: "Tunisia", flag: "🇹🇳" },
  { code: "TUR", name: "Turkey", flag: "🇹🇷", aliases: ["turkiye"] },
  { code: "TKM", name: "Turkmenistan", flag: "🇹🇲" },
  { code: "UGA", name: "Uganda", flag: "🇺🇬" },
  { code: "UKR", name: "Ukraine", flag: "🇺🇦" },
  { code: "ARE", name: "United Arab Emirates", flag: "🇦🇪", aliases: ["uae"] },
  { code: "GBR", name: "United Kingdom", flag: "🇬🇧", aliases: ["england", "scotland", "great britain"] },
  { code: "USA", name: "United States", flag: "🇺🇸", aliases: ["united states of america"] },
  { code: "URY", name: "Uruguay", flag: "🇺🇾" },
  { code: "UZB", name: "Uzbekistan", flag: "🇺🇿" },
  { code: "VEN", name: "Venezuela", flag: "🇻🇪" },
  { code: "VNM", name: "Vietnam", flag: "🇻🇳" },
  { code: "YEM", name: "Yemen", flag: "🇾🇪" },
  { code: "ZMB", name: "Zambia", flag: "🇿🇲" },
  { code: "ZWE", name: "Zimbabwe", flag: "🇿🇼" }
];

// Dual index: by ISO3 and normalized names
const BY_CODE = {};
const BY_NAME = {};

function cleanKey(str) {
  return (str || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

WORLD_COUNTRIES.forEach(item => {
  BY_CODE[item.code.toUpperCase()] = item;
  BY_NAME[cleanKey(item.name)] = item;
  if (item.aliases) {
    item.aliases.forEach(alias => {
      BY_NAME[cleanKey(alias)] = item;
    });
  }
});

/**
 * Resolves a vector country feature into clean { name, code, flag }.
 */
function resolveCountryFeature(feature) {
  const p = feature.properties || {};
  const rawName = (p.ADMIN || p.admin || p.name || p.NAME || p.name_en || "Unknown").trim();
  const rawCode = (p.ISO_A3 || p.iso_a3 || p.ISO3 || p.iso3 || p.ADM0_A3 || p.adm0_a3 || feature.id || "").toUpperCase().trim();

  // 1. Primary lookup by English name (circumvents Natural Earth's -99 ISO bugs)
  const normName = cleanKey(rawName);
  if (BY_NAME[normName]) {
    const match = BY_NAME[normName];
    return { name: rawName, code: match.code, flag: match.flag };
  }

  // 2. Secondary lookup by 3-letter code if valid
  if (rawCode && rawCode !== "-99" && BY_CODE[rawCode]) {
    const match = BY_CODE[rawCode];
    return { name: rawName, code: match.code, flag: match.flag };
  }

  // 3. Fallback: isolated unique slug and default globe
  const fallbackCode = (rawCode && rawCode !== "-99" && rawCode.length === 3)
    ? rawCode
    : rawName.toUpperCase().replace(/[^A-Z0-9]/g, "_");

  return { name: rawName, code: fallbackCode, flag: "🌐" };
}