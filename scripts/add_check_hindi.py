"""Adds the Hindi text of the Crop check page to translations/hi.json. Safe to run twice."""
import json

PATH = "translations/hi.json"
NEW = {
    "Crop check": "फ़सल जाँच",
    "km": "कि.मी.",
    "Check crop": "फ़सल जाँचें",
    "Crop check: does the climate of your district suit a crop?": "फ़सल जाँच: क्या आपके ज़िले की जलवायु इस फ़सल के अनुकूल है?",
    "Pick a district and a crop to see if the temperature, humidity and rain there look like places where that crop is major. This is a check, not a prediction.": "ज़िला और फ़सल चुनें और देखें कि वहाँ का तापमान, नमी और बारिश उन जगहों जैसी है या नहीं जहाँ यह फ़सल प्रमुख है। यह एक जाँच है, भविष्यवाणी नहीं।",
    "Pick a district and a crop. We compare the temperature, humidity and rain of that district with the districts where the crop is major, and tell you how close they are.": "ज़िला और फ़सल चुनें। हम उस ज़िले के तापमान, नमी और बारिश की तुलना उन ज़िलों से करते हैं जहाँ यह फ़सल प्रमुख है, और बताते हैं कि दोनों कितने पास हैं।",
    "This is a check, not a prediction and not farming advice. It sees climate only. It does not see water, soil, seed or market prices.": "यह एक जाँच है, भविष्यवाणी या खेती की सलाह नहीं। यह सिर्फ़ जलवायु देखती है। यह पानी, मिट्टी, बीज या बाज़ार भाव नहीं देखती।",
    "The climate looks like a good match for {crop}.": "जलवायु {crop} के लिए अच्छी तरह मेल खाती दिखती है।",
    "The climate is a partial match for {crop}.": "जलवायु {crop} से कुछ हद तक मेल खाती है।",
    "The climate does not look like a good match for {crop}.": "जलवायु {crop} से अच्छी तरह मेल खाती नहीं दिखती।",
    "Today {crop} is a major crop here. It covers {share}% of the area recorded for {season}.": "आज {crop} यहाँ एक प्रमुख फ़सल है। यह {season} के दर्ज क्षेत्र के {share}% में बोई जाती है।",
    "Today {crop} is grown here, but only on {share}% of the area recorded for {season}.": "आज {crop} यहाँ उगाई जाती है, पर {season} के दर्ज क्षेत्र के सिर्फ़ {share}% में।",
    "Today {crop} is not recorded here.": "आज {crop} यहाँ दर्ज नहीं है।",
    "So the climate may suit it, even though it is not major here. Water, soil, seed or prices may be the reason, and we cannot see those.": "यानी जलवायु इसके अनुकूल हो सकती है, भले ही यह यहाँ प्रमुख नहीं है। इसकी वजह पानी, मिट्टी, बीज या भाव हो सकते हैं, जो हम नहीं देख पाते।",
    "Farmers here do grow it widely, so something other than climate is probably helping, such as water or markets. Our check can be wrong.": "यहाँ किसान इसे बड़े पैमाने पर उगाते हैं, इसलिए जलवायु के अलावा कुछ और मदद कर रहा होगा, जैसे पानी या बाज़ार। हमारी जाँच ग़लत भी हो सकती है।",
    "points towards a match": "मेल की ओर इशारा करता है",
    "points away from a match": "मेल से दूर इशारा करता है",
    "Nearby districts with a similar or better climate for it": "आस-पास के ज़िले जहाँ इसके लिए मिलती-जुलती या बेहतर जलवायु है",
    "Nearby districts where {crop} does well": "आस-पास के ज़िले जहाँ {crop} अच्छी होती है",
    "Distance": "दूरी",
    "Today": "आज",
    "Major crop, {share}% of recorded area": "प्रमुख फ़सल, दर्ज क्षेत्र का {share}%",
    "Climate suits it, but it covers only {share}%": "जलवायु अनुकूल है, पर यह सिर्फ़ {share}% में है",
    "Distance is a straight line between district centres.": "दूरी ज़िलों के केंद्रों के बीच सीधी रेखा में है।",
    "We did not test {crop} in {district}, because the records for it cover only some districts. So we have no check to show.": "हमने {district} में {crop} की जाँच नहीं की, क्योंकि इसके रिकॉर्ड सिर्फ़ कुछ ज़िलों के हैं। इसलिए दिखाने के लिए कोई जाँच नहीं है।",
    "How good is this check? In our own test, when the model compared a district where {crop} is major with one where it is not, it put the right one higher {n} times out of 100. See the Crops page for all the checks.": "यह जाँच कितनी अच्छी है? हमारे अपने टेस्ट में, जब मॉडल ने एक ऐसे ज़िले की तुलना की जहाँ {crop} प्रमुख है और एक जहाँ नहीं है, तो उसने सही ज़िले को 100 में से {n} बार ऊपर रखा। सभी जाँचें फ़सलें पेज पर देखें।",
}
hi = json.load(open(PATH, encoding="utf-8"))
hi.update(NEW)
with open(PATH, "w", encoding="utf-8") as fh:
    json.dump(dict(sorted(hi.items())), fh, ensure_ascii=False, indent=1)
print("Hindi keys now:", len(hi))
