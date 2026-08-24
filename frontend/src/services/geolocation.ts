import axios from 'axios';

// Fallback to IPWHO if GPS is denied or fails
const IPWHO_API_KEY = "sk.9e697fbe4d5d172d10d9db17f6700b26b7490185349f3e31ae1a5c72e75ae42d";

// Mapping of states to languages
const STATE_LANGUAGE_MAP: { [key: string]: string } = {
    // South India
    "Karnataka": "Kannada",
    "Tamil Nadu": "Tamil",
    "Kerala": "Malayalam",
    "Andhra Pradesh": "Telugu",
    "Telangana": "Telugu",

    // West India
    "Maharashtra": "Marathi",
    "Gujarat": "Gujarati",

    // East India
    "West Bengal": "Bengali",
    "Odisha": "Odia",

    // North India / Hindi Belt
    "Delhi": "Hindi",
    "Uttar Pradesh": "Hindi",
    "Bihar": "Hindi",
    "Rajasthan": "Hindi",
    "Madhya Pradesh": "Hindi",
    "Haryana": "Hindi",
    "Punjab": "Punjabi",
    "Himachal Pradesh": "Hindi",
    "Uttarakhand": "Hindi",
    "Jharkhand": "Hindi",
    "Chhattisgarh": "Hindi",
    "Jammu and Kashmir": "Hindi",
    "Ladakh": "Hindi",
    "Chandigarh": "Hindi"
};

interface GeoLocationResponse {
    success: boolean;
    data: {
        geoLocation: {
            region: string; // This is usually the state/province
            country: string;
            city: string;
        }
    }
}

export const detectLocationAndLanguage = async (): Promise<string | null> => {
    // 1. Try Browser Geolocation (Permission based)
    try {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                timeout: 5000
            });
        });

        const { latitude, longitude } = position.coords;
        console.log("GPS Coordinates:", latitude, longitude);

        // Reverse Geocode
        // Using BigDataCloud Free API (Client-side friendly, no key needed for basic)
        const response = await axios.get(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`);

        if (response.data && response.data.principalSubdivision) {
            const region = response.data.principalSubdivision;
            console.log("GPS Detected Region:", region);
            const lang = STATE_LANGUAGE_MAP[region];
            if (lang) return lang;
        }
    } catch (gpsError) {
        console.warn("GPS Permission denied or failed, falling back to IP:", gpsError);
    }

    // 2. Fallback to IP-based
    try {
        const response = await axios.get(`https://api.ipwho.org/?apiKey=${IPWHO_API_KEY}&get=geoLocation`);

        if (response.data?.success && response.data?.data?.geoLocation?.region) {
            const region = response.data.data.geoLocation.region;
            console.log("IP Detected Region:", region);

            const language = STATE_LANGUAGE_MAP[region];
            if (language) {
                return language;
            }
        }
    } catch (ipError) {
        console.error("IP Location failed:", ipError);
    }

    return null;
};
