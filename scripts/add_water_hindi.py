"""Adds the Hindi text of the groundwater box to translations/hi.json. Safe to run twice."""
import json

PATH = "translations/hi.json"
NEW = {
    "Groundwater here": "यहाँ भूजल",
    "We also tried adding groundwater to the model as one more clue, and tested it on districts the model had never seen. Across all tested crops the score moved from {a} to {b} out of 100, and for the crops we show from {c} to {d}. Before the test we had set a bar: a gain of at least {bar} points. It did not reach the bar, so groundwater stays out of the model.": "हमने भूजल को मॉडल में एक और संकेत की तरह जोड़कर भी देखा, और उसे ऐसे ज़िलों पर परखा जो मॉडल ने कभी नहीं देखे थे। सभी परखी गई फ़सलों में स्कोर 100 में से {a} से {b} हुआ, और जो फ़सलें हम दिखाते हैं उनमें {c} से {d}। टेस्ट से पहले हमने एक पैमाना तय किया था: कम से कम {bar} अंक की बढ़त। वह पैमाना पूरा नहीं हुआ, इसलिए भूजल मॉडल से बाहर रहता है।",
    "Over-exploited": "अत्यधिक दोहन",
    "Critical": "गंभीर",
    "Semi-critical": "अर्ध-गंभीर",
    "Safe": "सुरक्षित",
    "Officially, {pct}% of the groundwater that nature refills in a year is pumped out. Assessed in March {year}.": "सरकारी आकलन के अनुसार, प्रकृति हर साल जितना भूजल भरती है, उसका {pct}% निकाल लिया जाता है। आकलन मार्च {year} का है।",
    "Where water is short, a crop that needs a lot of water may be hard to grow even if the climate suits it. Our check does not see this.": "जहाँ पानी कम है, वहाँ ज़्यादा पानी माँगने वाली फ़सल उगाना मुश्किल हो सकता है, भले ही जलवायु उसके अनुकूल हो। हमारी जाँच यह नहीं देखती।",
    "This number leaves out Malerkotla, which was made a separate district in 2021.": "इस संख्या में मालेरकोटला शामिल नहीं है, जिसे 2021 में अलग ज़िला बना दिया गया था।",
    "Source: Central Ground Water Board. Over-exploited means above 100%, critical 90 to 100%, semi-critical 70 to 90%, safe up to 70%. These are block-level counts added up for the district.": "स्रोत: केंद्रीय भूजल बोर्ड। अत्यधिक दोहन का मतलब 100% से ऊपर, गंभीर 90 से 100%, अर्ध-गंभीर 70 से 90%, और सुरक्षित 70% तक है। ये ब्लॉक स्तर की गिनती हैं जिन्हें ज़िले के लिए जोड़ा गया है।",
    "Groundwater is shown as plain facts from the Central Ground Water Board. We did not feed it into any model. Punjab is from the March 2024 assessment and Haryana from March 2022.": "भूजल की जानकारी केंद्रीय भूजल बोर्ड से सीधे तथ्यों की तरह दिखाई गई है। हमने इसे किसी मॉडल में नहीं डाला। पंजाब का आँकड़ा मार्च 2024 के आकलन से और हरियाणा का मार्च 2022 से है।",
}
hi = json.load(open(PATH, encoding="utf-8"))
for k, v in NEW.items():
    hi.setdefault(k, v)  # keep an existing translation if there already is one
with open(PATH, "w", encoding="utf-8") as fh:
    json.dump(dict(sorted(hi.items())), fh, ensure_ascii=False, indent=1)
print("Hindi keys now:", len(hi))
