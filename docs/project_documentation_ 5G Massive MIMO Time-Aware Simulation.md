# **אוניברסיטת בר-אילן** **המחלקה למדעי המחשב**

# **סימולציה של ערוץ תקשורת ותהליכי CSI ברשתות 5G / Beyond-5G, ברמת ה-PHY וה-RAN**

# **מסמך אפיון וסיכום פרויקט**

# **מוגש על ידי: עמרי ישראלי** **תעודת זהות: 322771379**

# **בהנחיית: פרופ' דוד סרנה**

# **תאריך הגשה: אפריל 2026**

# **תוכן עניינים:**

1.  [הגדרת הסימולציה](#1.-הגדרת-הסימולציה)  
2.  [דרישות מערכת והוראות התקנה](#2.-דרישות-מערכת-והוראות-התקנה)  
   1. [דרישות קדם](#דרישות-קדם)  
   2. [הוראות התקנה והרצה](#הוראות-התקנה-והרצה)  
3. [ארכיטקטורת המערכת](#3.-ארכיטקטורת-המערכת)  
   1. [נקודת הכניסה של הסימולציה](#entry-point---mainsimulation.m)  
   2. [מודולי המערכת](#מודולי-המערכת:)  
      1. [מודול ה-Config](#module-1:-config)  
      2. [מודול ה-Environment](#module-2:-environment)  
      3. [מודול ה-Mobility](#module-3:-mobility)  
      4. [מודול ה-Network](#module-4:-network)  
      5. [מודול ה-Simulation](#module-5:-simulation)  
      6. [מודול ה-Output](#module-6:-output)  
      7. [מודול ה-Tests](#module-7:-tests)  
      8. [מודול ה-Utils](#module-8:-utils)  
4. [שליטה בסימולציה](#4.-שליטה-בסימולציה)  
5. [הוראות הרצה](#5.-הוראות-הרצה)

6. ## [תוספות ושיפורים עתידיים](#6.-תוספות-ושיפורים-עתידיים)

7. [סיכום טכני](#7.-סיכום-טכני)  
8. [תוצאות לדוגמה](#8.-תוצאות-לדוגמה)

&nbsp;

## **1\. הגדרת הסימולציה** {#1.-הגדרת-הסימולציה}

הפרויקט הינו סימולציית רשת סלולרית דינמית המבוססת על מנוע הערוץ **Quadriga** (גרסה 2.8.1). מטרת המערכת היא לייצר Datasets עשירים ומדויקים לאימון מודלים של למידת מכונה (Machine Learning), תוך התמקדות בריאליזם, עקביות וביצועים.

**מאפיינים ייחודיים:**

* **דינמיות בזמן (Time-Aware):** הסימולציה אינה "צילום מצב" (Snapshot), אלא רצף אירועים מתמשך בו משתמשים נעים והערוץ משתנה.  
* **שכבת הקשר סביבתי (Context-Awareness):** בניגוד לסימולטורים סטטיים, מערכת זו מושפעת מחותמת הזמן (Datetime). מזג האוויר וגשם מחושבים בזמן אמת לפי מודל ITU-R ומשפיעים על הניחות, בעוד עומסי התעבורה ברשת (Interference) משתנים בהתאם לשעה ביום וליום בשבוע.  
* **שכבה מרחבית:** יצירת מפות דינמיות הכוללות אזורים שונים (פארקים, משרדים, אזורי תעשייה) באמצעות דיאגרמות Voronoi, המשפיעות על אופי התפשטות האות (LOS/NLOS).  
* **שכבת תנועה (Mobility):** מודלים המדמים תנועה רציפה של משתמשי קצה (UEs) במרחב, תוך תמיכה בתנועה אקראית או מבוססת מסלולים מוגדרים מראש (Trace-Based).  
* **שכבת רדיו ופיזיקה (PHY):** אינטגרציה עמוקה עם מנוע ה-Ray-Tracing הסטטיסטי QuaDRiGa, המאפשר חישוב מדויק של ערוצי Massive MIMO מרובי אנטנות, תוך התחשבות באפקט דופלר, פיזור זוויתי, והשהיות התפשטות.  
* **שכבת ניהול רשת (RAN):** מנגנון Handover היוריסטי מתקדם, המחשב קנסות עבירות בין פוליגונים שונים ומונע התחברויות "פינג-פונג" לא הגיוניות, בטרם ביצוע חישוב הערוץ הפיזיקלי המלא.  
* **ביצועים (Performance):** שימוש בחישוב מקבילי (Batch Processing) מול Quadriga כדי לאפשר הרצה של מאות משתמשים בזמן סביר.

**מ**דובר **בסימולציה פיזיקלית/ערוצית (PHY / channel-level)** שמותאמת היטב לתרחישי 5G, ולא בסימולציית מערכת 5G מלאה (RAN \+ MAC \+ Core).  היא כוללת עבודה בתדרי Sub-6GHz ו-mmWave, תמיכה ב-MIMO ו-Massive MIMO, עיצוב אלומות (Beamforming), והשפעות של ניידות משתמשים כגון Doppler, multipath ושינויים מרחביים-זמניים בערוץ. בנוסף, היא מאפשרת הפקת מדדי CSI מפורטים (כגון CQI, PMI, RI) ושליטה בתדירות ובאופן הדיווח שלהם, בהתאם למיקום, תנועה וסביבה (עירונית/כפרית), תוך התאמה למודלי ערוץ תקניים של 3GPP.  
המערכת תוכננה בארכיטקטורה מודולרית ומבוזרת (Object-Oriented), המאפשרת לחוקרים להחליף אלגוריתמים, להוסיף מודלים חדשים ולשלוף נתונים בצורה יעילה ומאובטחת (Data Validation), מבלי לפגוע בליבת החישוב הפיזיקלית.  
יחד עם זאת, זאת לא סימולציה מלאה של רשת 5G. הסימולציה אינה כוללת מימוש מלא של ה-**protocol stack** של 5G, ובפרט אינה מדמה את שכבות ה-**MAC**, **RLC** ו-**PDCP**, מנגנוני **scheduling** מלאים, **HARQ**, ניהול **QoS** או **network slicing**. בנוסף, אין בה ייצוג של **5G Core Network**, כולל רכיבים כגון **AMF**, **SMF** ו-**UPF**, ואין סימולציה של תהליכי **end-to-end signaling** או של **system-level latency**. כמו כן, הסימולציה אינה מייצגת התנהגות של **commercial gNB** או מימוש מלא של **O-RAN** בהתאם לתקני **3GPP**, אלא מתמקדת במידול ערוץ ותהליכים אלגוריתמיים ברמת ה-**PHY** וה-**RAN** בלבד.

---

&nbsp;

## **2\. דרישות מערכת והוראות התקנה** {#2.-דרישות-מערכת-והוראות-התקנה}

### **דרישות קדם** {#דרישות-קדם}

1. **MATLAB:** גרסה R2021a ומעלה (מומלץ R2023b לביצועים מיטביים).  
   נדרשים ה-Toolboxes הבאים:  
   * Communications Toolbox  
   * Phased Array System Toolbox (עבור חישובי האנטנות)  
   * Statistics and Machine Learning Toolbox (עבור חישובי Voronoi והתפלגויות)  
2. **Quadriga:** ספריית Quadriga Channel Model, גרסה **2.8.1**.  
   * *הערה:* גרסאות חדשות יותר עשויות לשנות את ה-API של *`qd_layout`* ולדרוש התאמות בקוד.  
3. **חומרה:** מומלץ מחשב עם לפחות 16GB RAM (עדיפות ל-32GB להרצות ארוכות) ומעבד מרובה ליבות (לחישובים מקביליים ב-MATLAB).

### **הוראות התקנה והרצה** {#הוראות-התקנה-והרצה}

1. הורד את קוד הפרויקט (Clone) מה-[GitHub](https://github.com/Omri154/5G-Massive-MIMO-Simulator) למחשב המקומי.&nbsp;  
2. הורד את תיקיית *`quadriga_src`* [מהאתר הרשמי של Quadriga](https://quadriga-channel-model.de/) וחלץ אותה לצד תיקיית הפרויקט (לא בתוכה, כדי לשמור על סדר).  
3. פתח את MATLAB ונווט לתיקיית הפרויקט.  
4. הוסף את תיקיית Quadriga ל-Path של MATLAB:  
   *addpath(genpath('../path\_to\_quadriga\_folder'));*  
5. הרץ את הפקודה:  
   main\_simulation

---

&nbsp;

## **3\. ארכיטקטורת המערכת** {#3.-ארכיטקטורת-המערכת}

המערכת בנויה בארכיטקטורה מודולרית המחולקת ל-8 מודולים (תיקיות) וקובץ כניסה ראשי. מבנה זה נבחר כדי להפריד בין הפיזיקה (Quadriga), הלוגיקה (ניהול זמן ותנועה) והנתונים (Config).

### **Entry Point \- mainSimulation.m** {#entry-point---mainsimulation.m}

קובץ זה מנהל את זרימת התוכנית (Workflow) המלאה:

* **אתחול:** טעינת `SimulationConfig.m` והוספת כל תת-התיקיות לנתיב ההרצה.  
* **יצירת סביבה:** קריאה למחוללי האזורים, תחנות הבסיס והמשתמשים לפי הגדרות ה-Seed לשמירה על שחזוריות.  
* **הלולאה הראשית (Time Loop):** קידום שעון הסימולציה בקפיצות זמן (dt) מוגדרות. בכל קפיצה מבוצעים:  
  * עדכון מיקומי משתמשים וניהול מעברים (Transitions) בין אזורי שטח מוסתרים/גלויים.  
  * עדכון וקטורי מהירות (במודל האקראי).  
  * ייצור דוחות CSI (הכוללים חישובי Handover ואת מנוע QuaDRiGa) במרווחי זמן מוגדרים.  
* **סיום ושמירה:** איסוף הנתונים מכל הרכיבים והעברתם ל-`ResultsManager.m` להפקת תוצרים ויזואליים ושמירת קבצי נתונים.

כמו כן, קובץ זה מנוהל בצורה חכמה הגורמת לסימולציה לרוץ ביעילות באמצעות המנגנונים הבאים:

* **ניהול זיכרון:** מבצע הקצאה מראש (Pre-allocation) של המטריצות לשמירת התוצאות. גודל הזיכרון הנדרש הוא ליניארי ביחס ל:NUEs X Nreports. עבור הרצות סטנדרטיות (100 משתמשים, 5 דקות) הצריכה זניחה (כמה MB בודדים). להרצות ענק (מיליוני דוגמאות), יש לשנות את הקוד לכתיבה מחזורית לדיסק (Batch Writing) כדי לא לחרוג מה-RAM.&nbsp;  
  כדי לתמוך בבקשות דינמיות של CSI (כאשר מספר הדיווחים אינו ידוע מראש) ובהרצות ענק ללא חריגת RAM, ייושם מנגנון **Buffer & Flush**. יוקצה באפר בגודל קבוע (למשל 10,000 דיווחים). כאשר הבאפר יתמלא, הנתונים יכתבו ברצף (Append) לקובץ הדיסק, והבאפר יתאפס וידרס מחדש. כך תובטח צריכת זיכרון קבועה לאורך כל הסימולציה.  
* הסימולציה מבוססת על זמן אבסולוטי (בשניות) ולא על מספר איטרציות. היא רצה מרגע 0 ועד ל-total\_duration. בכל איטרציה, מקודם שעון הסימולציה בצעד קבוע של position\_update\_dt (רזולוציית התנועה), המבטיח עדכון רציף ופיזיקלי של מיקומי המשתמשים.  
* **CSI לפי דרישה (On-Demand CSI):** בעוד שברירת המחדל היא דיווח מחזורי (לפי `csi_report_interval`), הארכיטקטורה מאפשרת שליפה דינמית. נצטרך לבנות מודולים חיצוניים (כגון שרת Scheduling) שיוכלו לעקוף את המנגנון המחזורי ולקרוא לפונקציית הפקת ה-CSI עבור משתמש ספציפי או קבוצת משתמשים בכל רגע נתון על ציר הזמן.&nbsp;  
  &nbsp;

### **מודולי המערכת:** {#מודולי-המערכת:}

המערכת בנויה בארכיטקטורה מודולרית המחולקת ל-8 מודולים, המאפשרת לחוקרים להחליף אלגוריתמים, להוסיף מודלים חדשים ולשלוף נתונים בצורה יעילה ומאובטחת, מבלי לפגוע בליבת החישוב הפיזיקלית.

### **Module 1: Config** {#module-1:-config}

* **`simulation_config.m`**: מרכז את כל הפרמטרים המשתנים.&nbsp;  
  * **תפקיד:** "המוח" של המערכת. מחזיר `struct` המכיל את כל הפרמטרים.  
  * **פרטים:** מגדיר את תצורת האנטנות (MIMO 64x64 \- יש 64 אנטנות משדרות ו64 אנטנות קולטות, כלומר 64 משדרים64X קולטים), גודל המשטח, זרעים (Seeds) לרנדומליות, ופרופילי תעבורה ומזג אוויר. הקוד תומך בשינוי דינמי (למשל, שינוי מ-200x200 ל-1000x1000 מטר) ללא שכתוב לוגיקה. (ניתן לשנות את הנתונים בקובץ עצמו, למשל לשנות מ-8 פוליגונים ל-10 פוליגונים, לשנות את המשטח מ200X200 מטרים ל500X100, וכו').  
  * אחראי לשמור גם על חתימת הזמן של הרצת הסימולציה (ניתן לשנות לאיזה תאריך ושעה שרוצים): ![][image1]  
  * בנוסף, קובץ זה מכיל פרופילי תעבורה ומזג אוויר. כלומר, לכל חודש, ולכל סוג אזור מוגדר הסיכוי לגשם ומה עוצמת הגשם בהתאם לחודש (למשל בינואר הסיכוי שיהיה גשם קל הוא 0.3, הסיכוי לגשם כבד הוא 0.1, ואחרת כלומר 0.6 יהיה ללא גשם). כמו כן, מוגדר גם רמת העומס באזור מסוים בהתאם ליום והשעה (למשל עבור מרכז קניות באמצע שבוע בבוקר יהיה מקדם עומס 0.3 כלומר בינוני-נמוך, ועבור מרכז קניות בסוף שבוע בצהריים מקדם העומס יהיה 0.9, כלומר גבוה מאוד).&nbsp;  
    הסיכויים לגשם ורמת העומס נקבעו בהתאם למציאות, וניתנים לשינוי במידת הצורך.&nbsp;  
  * ההגדרות האלה נמצאות בקובץ config. במזג אוויר זה סיכויים, כאשר המספר הראשון זה סיכוי למזג אוויר נוח ללא גשם, המספר השני זה סיכוי לגשם קל, והמספר השלישי זה סיכוי לגשם כבד. (ההבדלים במזג האוויר זה כמה הפרעות נוסיף לחישוב עוצמת האות). ובגלל שאלה הסתברויות אז צריך שזה יסתכם ל-1.&nbsp;  
    דוגמה לסיכויים למזג אוויר:&nbsp;  
    ![][image2]  
    &nbsp;  
  * לגבי רמת העומס, לכל אזור יש 5 טווחי שעות. מחצות עד שש בבוקר \- זה מוגדר להיות לילה. משש בבוקר עד עשר בבוקר, זה מוגדר להיות בוקר. מעשר בבוקר עד חמש בערב, זה מוגדר להיות צהריים (midday). מחמש בערב עד עשר בלילה, זה מוגדר להיות ערב. ומעשר בלילה עד חצות, זה מוגדר להיות מאוחר (late). ולכל טווח שעות אפשר לשנות את רמת העומס שרוצים. זה צריך להיות ערך בין 0 ל-1 כאשר 0 זה אין עומס בכלל, ו-1 זה עמוס לגמרי.  
    דוגמה להגדרת רמת עומס בהתאם לאזור כלשהו לפי שעות:  
    ![][image3]

### **Module 2: Environment** {#module-2:-environment}

* **`AreaGenerator.m`**:  
  * **תפקיד:** יצירת הטופולוגיה של השטח.  
  * **פונקציות מפתח:**  
    * *`generate`*: מחלק את השטח לפוליגונים באמצעות Voronoi Tessellation.  
    * *`assign_matching_scenario`*: מצמיד לכל אזור פרופיל Quadriga מתאים (למשל: Shopping Center מקבל `3GPP_38.901_UMi_NLOS`).

דוגמה למשטח שמחולק לפוליגונים בעזרת voronoi:

&nbsp;

&nbsp;

&nbsp;

* מה זה הפרופילי quadriga?  
  פרופיל quadriga (או scenarios כפי שנקראים בquadriga) הם ההגדרות הפיזיקליות של סוג האיזור ש-quadriga יגריל ויתן לאזור הזה. הscenario מוגדר מסוג הסביבה (urban micro/urban macro/rural macro/indoor hotspot), ומקשר עין (LOS \- line of sight/NLOS \- non line of sight). בפועל, הפרופילים האלה משפיעים על החישובים המתמטים ועל הסטוכסטיות של התרחיש:  
  כאשר מגדירים פרופיל, QuaDRiGa טוענת סט של פרמטרים סטטיסטיים (LSP \- Large Scale Parameters) אשר משפיע ישירות על:  
1. **Path Loss Formula:** הנוסחה שמחשבת כמה הנחתה יש למרחק (למשל, ב-RMa ההנחתה תהיה פרופורציונלית ל-d2, בעוד שב-UMi\_NLOS היא תהיה קרובה ל-d3.5).  
2. **Delay Spread:** הפער בזמנים בין הגעת הקרן הראשונה לקרן האחרונה (גדול יותר בערים בגלל החזרים מרחוק).  
3. **Angular Spread:** עד כמה הקרניים "מרוחות" במרחב (קריטי לחישובי MIMO ו-Beamforming).  
4. **מספר ה-Clusters:** כמה "מקבצי החזרות" (קירות, בניינים) התוכנה מגרילה סביב המשתמש.&nbsp;

### **Module 3: Mobility** {#module-3:-mobility}

המודול האחראי על תנועת המשתמשים במרחב הגיאוגרפי. המערכת תומכת בשני מודלים עיקריים שניתנים להחלפה:

* **מודל תנועה רנדומלי במרחב \- `RandomWalkModel.m`**:  
  * **תפקיד:** מנוע הפיזיקה של תנועת המשתמשים.  
  * **לוגיקה:** מודל "ביליארד" \- כל משתמש מגריל נקודת התחלה, נע בקו ישר, ומשנה כיוון ומהירות כל X שניות, ומבצע החזרה (Reflection) בהתנגשות בגבולות המפה.  
  * דוגמה למסלולים של 35 משתמשים במשך 90 שניות:

&nbsp;

  * כדי לייצר  מודל של מקומות ספציפיים (למשל עבודה/בית/בית ספר וכו'), נהפוך את המשטח להיות גרף עם נקודות העניין בתור הצמתים, והכבישים והמדרכות בתור הקשתות. (ב-MATLAB כבר ממומשים אובייקטים ליצירת גרפים). ואז על ידי דייקסטרה או אלגוריתם למציאת מסלול קצר ביותר נקדם את המשתמש על המסלול הזה לכיוון הנקודה שהוא צריך להגיע בסוף.&nbsp;  
  * לגבי העניין של קבוצת משתמשים שנעים ביחד, פתרון מוכר שמשתמשים בו זה (RPGM (Reference Point Group Mobility. למשל עבור קבוצה של 3 משתמשים, נקבע אחד מהמשתמשים להיות המנהיג שהוא בפועל יתקדם על המפה, ועבור השניים האחרים, נוסיף סטייה של חצי מטר למשל מהמנהיג, ונחשב את הערוץ שלהם בהתאם למיקום הזה.

* **מודל תנועה מבוסס עקבות \- TraceBasedModel.m:**&nbsp;  
  * מודל זה, מאפשר תנועת משתמשים המוכתבת על ידי קובץ קלט חיצוני בפורמט CSV.&nbsp;  
  * **מבנה הנתונים:** קובץ הקלט מגדיר עבור כל משתמש סדרת נקודות ציון (Waypoints) הכוללות מיקום (x, y) וזמן עזיבה (Departure Time). המערכת תומכת במספר משתנה של נקודות לכל משתמש.  
  * דוגמה לקובץ קלט תקין:&nbsp;  
    בהזנת זמן היציאה יש לשים את השעה המלאה, כלומר כולל שניות.&nbsp;  
    (באקסל מוצג פורמט זמן קצר, ולכן לא מוצגות כאן השניות).  
    &nbsp;  
  * **אינטרפולציה ופיזיקה:** המיקום מחושב בזמן אמת באמצעות אינטרפולציה ליניארית בין נקודות הציון. המהירות אינה מוזנת ידנית אלא נגזרת פיזיקלית מהמרחק ומהזמן שבין הנקודות, מה שמבטיח עקביות בין התנועה במפה לבין אפקט הדופלר בחישובי הערוץ.&nbsp;  
  * **מימוש אופטימלי (Stateful):** המודל ממומש כאובייקט השומר את מצב האינדקס הנוכחי עבור כל UE. תכנון זה מאפשר עדכון מיקום בסיבוכיות של (O(1 ללא צורך בסריקה חוזרת של קובץ הקלט בכל צעד זמן.  
  * **חוסן וולידציה:** המודל כולל מנגנוני וולידציה המוודאים שהמהירויות הנגזרות הגיוניות פיזיקלית, ומפעיל מנגנון "Fallback" (מיקום נייח) עבור משתמשים שאינם מופיעים בקובץ הקלט.  
  * דוגמה לתנועת משתמשים באמצעות המודל החדש:&nbsp;  
    בתמונה מופיעים 15 משתמשים, שכל אחד מהם הולך מנקודה א' לנקודה ב' וחוזר לנקודה א' (כפי שמופיע בקובץ הקלט הספציפי להרצה זו).  
    &nbsp;

&nbsp;

&nbsp;

### **Module 4: Network** {#module-4:-network}

* **`BaseStationManager.m`**:  
  * **תפקיד:** ניהול תחנות הבסיס (BS).  
  * **פונקציות מפתח:** יוצר מערכי אנטנות **Massive MIMO 8x8** (כלומר 64 אלמנטים) בתצורת Cross-Polarized, כולל שליטה על כיוון (Azimuth) והטיה (Downtilt).  
* **`UserEquipmentManager.m`**:  
  * **תפקיד:** ניהול המשתמשים (UEs).  
  * **פונקציות מפתח:** מסנכרן בין המיקום הפיזי של המשתמש (ממודול ה-Mobility) לבין אובייקט האנטנה ב-Quadriga.

### **Module 5: Simulation** {#module-5:-simulation}

מודול זה מכיל את "המנועים" של הסימולציה.

* **`CSIReporter.m`**:  
  * **תפקיד:** הממשק מול Quadriga. גרסה זו עברה אופטימיזציה מסיבית.  
  * **חידוש:** במקום לחשב ערוץ לכל משתמש בנפרד, הוא מקבץ משתמשים לפי אזור ו-BS ומריץ **קריאה אחת** (Batch) ל-Quadriga.  
  * **Context:** מוסיף את השפעות מזג האוויר והעומס על הנתונים הגולמיים.  
  * **מנגנון בחירת תחנת בסיס:** כדי לדמות בצורה ריאליסטית את תהליך ה-Handover ולמנוע התחברות נאיבית לפי מרחק גיאומטרי בלבד, יושמה במערכת ארכיטקטורה דו-שלבית:  
    * **שלב בחירה היוריסטי:** הפונקציה *`find_serving_bs`* מוקצית לבחירת התחנה המשרתת. היא מעריכה את ה-RSRP עבור כל תחנות הבסיס על סמך ניחות מרחב חופשי (FSPL) בתוספת קנס חציית אזורים (Cross-Area Propagation Penalty) דטרמיניסטי. הלוגיקה משקללת את סוג הסביבה (LOS/NLOS) גם במיקום ה-UE וגם במיקום ה-BS. במקרים של מעבר בין אזורים מוסתרים, מופעל קנס (עד 15dB) המשקף את הימצאותם של מכשולים פיזיים (מבנים וכבישים). מנגנון זה מאפשר ל-UE להתחבר בצורה חכמה לתחנה רחוקה יותר אם קיים אליה קשר עין (LOS) נקי יותר.  
    * **שלב חישוב הפיזיקה:** החלטת ההתחברות משלב 1 מועברת למנוע QuaDRiGa. בשלב זה מבוצע חישוב מדויק של הערוץ (CSI, SINR, RSRP, CQI) על סמך ray-tracing סטטיסטי. חשוב להדגיש כי הקנס ההיוריסטי משלב 1 משמש אך ורק לקבלת ההחלטה הניהולית ואינו נלקח בחשבון בחישוב הפיזיקלי הסופי, מה שמונע עיוות נתונים ("קנס כפול").  
* **`TimeManager.m`**:  
  * **תפקיד:** ניהול שעון הסימולציה.  
  * **לוגיקה:** מנהל מוני זמן מדויקים כדי לקבוע מתי לעדכן מיקום (כל 0.1s) ומתי להפיק דוח CSI (כל 0.5s), תוך מניעת שגיאות עיגול (Floating Point Drift).  
* **`TransitionManager.m`**:  
  * **תפקיד:** טיפול במעברים בין אזורים.  
  * **לוגיקה:** מחשב *`blend_factor`* כדי לאפשר מעבר חלק של ערוץ התקשורת כאשר משתמש חוצה גבול בין שני אזורי Voronoi.  
  * **מנגנון המעבר וחישוב ה-*blend\_factor*:** בעולם האמיתי, מעבר בין אזור גיאוגרפי אחד לאחר (למשל, מיציאה משכונה צפופה לכביש פתוח) לא גורם לקפיצה מיידית וחדה בעוצמת הקליטה (RSRP) או באיכות האות. כדי לדמות זאת, ה-TransitionManager מגדיר "אזורי חפיפה" (Transition Zones) בין הפוליגונים של Voronoi.  
  * **איך זה עובד?** הלוגיקה מוצאת עבור כל משתמש את שני הזרעים (Seeds) הקרובים אליו ביותר. אם ההפרש בין המרחקים לשני הזרעים קטן מפרמטר המוגדר מראש (transition\_width) (כרגע ה-transition\_width מוגדר להיות 10 מטרים), המערכת מזהה שהמשתמש נמצא באזור המעבר.  
  * **מהו ה-*blend\_factor*?** זהו מקדם (בין 0 ל-1) המייצג את "משקל" הקרבה של המשתמש לכל אחד משני האזורים. מקדם של 0.5 אומר שהמשתמש נמצא בדיוק על קו הגבול התיאורטי.  
  * **על מה הוא משפיע?** ה-*blend\_factor* משמש את ה-*CSI\_Reporter* כדי לבצע אינטרפולציה (מיצוע משוקלל) בין תכונות הערוץ של אזור A לתכונות של אזור B. פעולה זו מבטיחה דעיכה או התחזקות חלקה ורציפה של מדדי ה-CSI, ומונעת "רעש מלאכותי" וקפיצות לא הגיוניות ב-Dataset שישמש את מודל ה-ML.&nbsp;

### **Module 6: Output** {#module-6:-output}

* **`ResultsManager.m`**:  
  * **תפקיד:** אחראי על ריכוז המידע, עיבודו ויצירת גרפים לויזואליזצית המידע.  
  * **תוצרים:** שומר קבצי CSV (אחד לכל משתמש \+ קובץ מרוכז), ומייצר אוטומטית סט של 8 גרפים לניתוח ביצועים (מפות חום, התפלגות SINR, מסלולי תנועה ועוד).

&nbsp;

### **Module 7: Tests** {#module-7:-tests}

מכיל בדיקות יחידה (Unit Tests) וסקריפטים לווידוא תקינות המודולים השונים לפני הרצה מלאה.

**מה נבדק בבדיקות הללו?** בדיקות אלו נועדו לוודא שכל מודול מתפקד כראוי באופן עצמאי, לפני שמשלבים אותו במנוע הראשי.

* **בדיקות תנועה (Mobility):** מוודאות שמשתמשים לא יוצאים מגבולות המפה (בדיקת מנגנון ה-Reflection בקירות) ושהמהירויות שמוגרלות נשארות בגבולות המינימום והמקסימום המותרים.  
* **בדיקות גיאומטריה:** מוודאות שאלגוריתם ה-Voronoi ופונקציית מציאת האזור (Nearest Neighbor) משייכים כל קואורדינטה לאזור הנכון במאת האחוזים.  
* **בדיקות מנהלי הרשת (BS/UE Managers):** מוודאות שהאובייקטים של QuaDRiGa נוצרים בהצלחה, ושמערכי האנטנות אכן מכילים את המספר המדויק של האלמנטים שהוגדר בקונפיגורציה (למשל: וידוא יצירת 64 אלמנטים פיזיים לכל תחנת בסיס).

### **Module 8: Utils** {#module-8:-utils}

ספריות עזר לשימוש חוזר.

* **`GeometryUtils.m`**: חישובי מרחק, זוויות, ומציאת האזור הקרוב ביותר.  
* **`TrafficUtils.m`**: חישוב עומס הרשת (0-1) בהתאם לשעה ביום וסוג האזור (למשל: משרד עמוס בבוקר וריק בלילה).  
* **`WeatherUtils.m`**: המרת תאריך להסתברות גשם, וחישוב ניחות (Attenuation) לפי מודל ITU-R.  
* **`ValidationUtils.m`**: בדיקות תקינות (Assertions) למניעת הרצת סימולציה עם פרמטרים שגויים.  
  קובץ זה מתפקד כ"שומר הסף" של הסימולציה, ומבצע סדרת בדיקות קריטיות (Assertions) המפוצלות לשני שלבים עיקריים:  
1. **בדיקות קדם-ריצה (Config Validation):** לפני שהסימולציה מתחילה, הקוד בודק שקובץ ה-Config הגיוני פיזיקלית.  
   * וידוא שמידות המשטח (*area\_width* ו-*area\_height*) חיוביות.  
   * וידוא שמספר אזורי ה-Voronoi הגיוני (בין 2 ל-20 אזורים).  
   * וידוא שקיימת לפחות תחנת בסיס אחת (BS) ומשתמש אחד (UE), ושלכולם יש לפחות אנטנת שידור (Tx) ואנטנת קליטה (Rx) אחת.  
2. **בדיקות פוסט-ריצה (CSI Metrics Validation):** בסיום הסימולציה, מתבצעת בקרת איכות על הנתונים שהופקו כדי להבטיח שה-Dataset תקין ללמידת מכונה.  
   * הקוד מסכם את מספר הדיווחים שנוצרו בפועל מול המספר המצופה.  
   * הוא בוחן את ערכי ה-RSRP וה-SINR המחושבים ומוודא שהם נופלים בתוך טווחים (Ranges) פיזיקליים הגיוניים. המערכת בודקת ערכי מינימום ומקסימום, ומחשבת ממוצעים כדי לוודא שאין חריגות כמו ערכי NaN או אינסוף (Inf) שעשויים להיווצר כתוצאה מחילוק באפס באזורים שוממים.  
* **`GenerateTestCSV.m`:** מייצר קובץ CSV לדוגמה להרצת מודל התנועה מבוסס העקבות לפי מספר הUEs שמוגדרים בקובץ הconfig, בתוך התיקייה שמוגדרת בקובץ הconfig. בחירת המחדל היא יצירת הקובץ בתוך תיקיית data תחת תיקיית הפרויקט הראשית. ניתן לשנות את תיקיית היעד בקובץ הconfig:

---

&nbsp;

## **4\. שליטה בסימולציה** {#4.-שליטה-בסימולציה}

כל השליטה מתבצעת דרך הקובץ *`simulation_config.m`*.  
 אין צורך לשנות קוד במודולים האחרים.

**פרמטרים עיקריים לשינוי:**

1. **Seeds (זרעים):**  
   * *`random_seed_areas`*: קובע את צורת המפה (חלוקת ה-Voronoi).  
   * *`random_seed_mobility`*: קובע את מסלולי התנועה של המשתמשים (במודל ההליכה הרנדומלי).  
2. **זמן:**  
   * *`simulation_datetime`*: קובע את העונה (גשם) ואת השעה (עומס).  
   * *`total_duration`*: אורך הסימולציה בשניות.  
3. **רשת:**  
   * *`ue.num`*: מספר המשתמשים.  
   * *`bs.num_tx`*: מספר אנטנות ל-BS (מוגדר כ-64).&nbsp;  
4. **תנועה:**

כדי להחליף בין מודלי התנועה השונים, השינויים שצריך לבצע הינם:

* החלפה ממודל התנועה מבוסס העקבות למודל התנועה הרנדומלי:  
  *`ב-config.mobility.model:`* להחליף מ-'trace\_based' ל- 'random\_walk' בשביל מודל ההליכה הרנדומלי.  
  * החלפה ממודל התנועה הרנדומלי למודל התנועה מבוסס העקבות:  
    *`ב-config.mobility.model:`* להחליף מ-'random\_walk' ל- 'trace\_based' בשביל מודל ההליכה מבוסס עקבות. רק חשוב לדאוג לקובץ קלט בפורמט הנכון בתוך תיקיית data כמו בדוגמה הבאה:

---

## **5\. הוראות הרצה** {#5.-הוראות-הרצה}

כדי להריץ את הסימולציה ולקבל את הנתונים:

1. פתח את התיקייה הראשית ב-MATLAB.  
2. הרץ את הפקודה: *main\_simulation*  
3. **מה קורה בזמן הריצה?**  
   * המערכת תאתחל את כל המודולים.  
   * תודפס הקצאת הזיכרון (Memory Allocation) הצפויה.  
   * לולאת הזמן תרוץ ותדפיס סטטוס התקדמות כל 30 שניות.  
4. **בסיום הריצה:**  
   * תיפתח תיקייה חדשה תחת *`results/simulation_YYYYMMDD_HHMMSS`*.  
   * קבצי ה-CSV יישמרו בתיקיית *`csv`*.  
   * הגרפים יישמרו בתיקיית *`figures`*.  
   * ייפתח דוח HTML מסכם בדפדפן.

---

## 

## **6\. תוספות ושיפורים עתידיים** {#6.-תוספות-ושיפורים-עתידיים}

פרק זה מיועד לחוקרים ומפתחים אשר ממשיכים את העבודה על הפרויקט. הוא כולל תכנון ארכיטקטוני לשיפורים שנדחו  לצורך הגעה ליציבות פונקציונלית.&nbsp;

### **שיפורים ופיתוחים עתידיים מומלצים:**

1. **הגברת ההטרוגניות במערכי האנטנות של המשתמשים:**  
   **תיאור הבעיה:** בגרסה הנוכחית, בתוך הפונקציה *`run_quadriga_batch`* (בקובץ CSIReporter.m), ההשמה *`{layout.rx_array = rx_arrays{1`* גורמת לכך שכל המשתמשים (UEs) ב-Batch מקבלים את תבנית הקרינה ומערך האנטנות של המשתמש הראשון בלבד. הדבר מבטל את השונות (Spatial Diversity) בין מכשירים שונים (למשל 4x4 MIMO מול 1x1 SISO).  
   **התיקון המתוכנן:** מנוע QuaDRiGa יודע לקבל Cell Array מלא. יש לשנות את ההשמה ל-*`layout.rx_array = rx_arrays;.`* חשוב לוודא שמנהל המשתמשים אכן מקצה אנטנות בעלות אוריינטציה שונה או מספר אלמנטים שונה לכל UE. ניתן לבצע זאת על ידי הוספת מערך האנטנות הרצוי לכל UE יחד עם נקודת ההתחלה שלו בקובץ הקלט של מודל התנועה החדש.&nbsp;  
2. **שינוי מהירות אסינכרוני למשתמשים:**  
   **תיאור הבעיה:** בשימוש במודל התנועה האקראי (RandomWalkModel), הפונקציה *`time_manager.should_update_velocities()`* בלולאה הראשית גורמת לכך שכל המשתמשים בסימולציה משנים כיוון ומהירות באותה השנייה בדיוק (למשל כל 10 שניות). זה יוצר דפוס תנועה מלאכותי.  
   **התיקון המתוכנן:** להעביר את הטיימר של עדכון המהירות לתוך אובייקט ה-UE עצמו. כל משתמש יחזיק משתנה פנימי של *`time_to_next_turn`*, שיקבל ערך אקראי בעת ההיווצרות שלו. עדכון המהירות יקרה באופן עצמאי לכל משתמש בהתאם לשעון הפרטי שלו.  
3. **אופטימיזציה ומטמון לבחירת תחנת בסיס:**  
   **תיאור הבעיה:** הפונקציה *`find_serving_bs_`* מבצעת עבודת חישוב מאומצת בכל אירוע של דיווח CSI (כל חצי שנייה). בפועל, משתמשים סלולריים אינם משנים תחנת בסיס בתדירות כזו.  
   **התיקון המתוכנן:** להוסיף Cache לכל משתמש. המערכת תחפש תחנת בסיס חדשה רק אם ה-UE חצה גבול של אזור (Voronoi Border), או אם עברו X שניות/מטרים מאז חישוב ה-Handover האחרון. הדבר יקטין דרסטית את זמן ריצת הסימולציה.  
4. **לוגיקת מעברים מתקדמת בין פוליגונים:**  
   **תיאור הבעיה:** במודול TransitionManager, הלוגיקה הנוכחית מטפלת במעבר בין שני אזורים בלבד ((area\_pair(2). במצב קצה שבו משתמש נע בדיוק על הקודקוד המשותף לשלושה (או יותר) תאי Voronoi, ההשפעה של האזור השלישי נזנחת.  
   **התיקון המתוכנן:** הרחבת האלגוריתם כך שיחזיר מערך משקלים לכל האזורים הסמוכים בהתאם למרחק האוקלידי שלהם מנקודת המשתמש, ומיצוע פרמטרי הערוץ (Blend) על פני כולם.  
5. **גמישות במודל מזג האוויר:**  
   **תיאור הבעיה:** בקובץ WeatherUtils.m, קיימת הטמעה קשיחה (Hardcoded) של מזג אוויר (שכרגע מוגדר למזג אוויר ים תיכוני של ישראל).&nbsp;  
   \*יש גם בדיקה שמחייבת שלא יהיה גשם ביולי/אוגוסט, ואם ישנו את מזג האוויר לפרופיל אחר, למשל דרומי כמו אוסטרליה, שם גשם בקיץ זה דבר נפוץ, המערכת תשנה את זה שחודשי הקיץ יהיו יבשים בהכרח.  
   **התיקון המתוכנן:** לחשוף את אופי מזג האוויר ואת עוצמת הגשם (mm/hr) כפרמטרים דינמיים בקובץ SimulationConfig.m, או לשאוב אותם מתוך מערך נתונים היסטורי של מטאורולוגיה מסונכרן עם ציר הזמן של המערכת.

---

##### **7\. סיכום טכני** {#7.-סיכום-טכני}

הסימולציה הנוכחית מייצגת State-of-the-Art בשימוש ב-Quadriga עבור יצירת Data. השילוב של **Massive MIMO**, **Batch Processing** ב-CSI Reporter, וניהול **Context** (זמן/מזג אוויר) מבטיח שהנתונים שיופקו יהיו ריאליסטיים, מגוונים ומתאימים למחקר מתקדם.

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

##### 

##### 

###### ---

###### **8\. תוצאות לדוגמה** {#8.-תוצאות-לדוגמה}

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

**דוגמה לחלק מהדיווחים של UE מספר 1:**&nbsp;

**Bar-Ilan University**  
**Department of Computer Science**

&nbsp;

**Simulation of Communication Channel and CSI Processes in 5G / Beyond-5G Networks, at the PHY and RAN Levels**

&nbsp;

**Project Documentation**

&nbsp;

**Submitted By: Omri Israeli**

**ID Number: 322771379**

&nbsp;

**Supervised by: Prof. David Sarne**

&nbsp;

**Submission Date: April 2026**

**Table of Content:**

&nbsp;

1. [Simulation Definition](#1.-simulation-definition)  
2. [System Requirements and Installation Instructions](#2.-system-requirements-and-installation-instructions)  
   1. [Prerequisites](#prerequisites)  
   2. [Installation and Run Instructions](#installation-and-run-instructions)  
3. [System Architecture](#3.-system-architecture)  
   1. [Entry Point of the Simulation](#entry-point---mainsimulation.m-1)  
   2. [System Modules](#the-system-modules:)  
      1. [Config Module](#module-1:-config-1)  
      2. [Environment Module](#module-2:-environment-1)  
      3. [Mobility Module](#module-3:-mobility-1)  
      4. [Network Module](#module-4:-network-1)  
      5. [Simulation Module](#module-5:-simulation-1)  
      6. [Output Module](#module-6:-output-1)  
      7. [Tests Module](#module-7:-tests-1)  
      8. [Utils Module](#module-8:-utils-1)  
4. [Simulation Control](#4.-simulation-control-\(configuration\))  
5. [Running the Simulation](#5.-running-the-simulation)  
6. [Future Additions and Improvements](#6.-future-additions-and-improvements)  
7. [Technical Summary](#7.-technical-summary)  
8. [Example Results](#8.-example-results)

## **1\. Simulation Definition** {#1.-simulation-definition}

&nbsp;

This project is a dynamic, time-stepped simulation system designed for evaluating and researching the performance of advanced cellular networks (5G and Beyond) in complex urban environments. The primary goal of the simulation is to generate rich, realistic datasets of Channel State Information (CSI), including metrics such as RSRP, SINR, and CQI for training Machine Learning models, focusing on realism, consistency, and performance.

The project is a dynamic cellular network simulation based on the **Quadriga** channel engine (version 2.8.1).

&nbsp;

**Unique Characteristics:**

The simulator integrates several complex layers:

* **Spatial Layer:** Generates dynamic maps containing diverse zones (parks, commercial areas, highways) using Voronoi diagrams, which dictate the signal propagation characteristics (LOS/NLOS).  
* **Mobility Layer:** Models simulating continuous movement of User Equipment (UE) in space, supporting both random movement and pre-defined trajectory-based movement (Trace-Based).  
* **Radio and Physics (PHY) Layer:** Deep integration with the QuaDRiGa statistical Ray-Tracing engine, enabling precise calculation of multi-antenna Massive MIMO channels (e.g., 64x4), factoring in Doppler effects, angular spread, and delay spread.  
* **Context-Awareness Layer:** Unlike static simulators, this system is influenced by timestamps (Datetime). Real-time weather and rain attenuation are calculated using the ITU-R model, while network traffic loads (Interference) fluctuate based on the time of day and day of the week.  
* **Network Management (RAN) Layer:** An advanced heuristic Handover mechanism that calculates traversal penalties across polygons, preventing illogical "ping-pong" connections prior to the full physical channel computation.  
* **Time-Aware:** The simulation is not a "Snapshot," but a continuous sequence of events where users move and the channel changes.  
* **Massive MIMO:** Full implementation of base stations with an 8x8 antenna array (a total of 64 elements).  
* **Performance:** Utilization of parallel computation (Batch Processing) with Quadriga to enable running hundreds of users in a reasonable time.

This is a **physical/channel-level (PHY / channel-level) simulation** well-suited for 5G scenarios, and not a full 5G system simulation (RAN \+ MAC \+ Core). It includes operation in Sub-6GHz and mmWave frequencies, support for MIMO and Massive MIMO, Beamforming, and effects of user mobility such as Doppler, multipath, and spatio-temporal changes in the channel. Additionally, it allows for the extraction of detailed CSI metrics (such as CQI, PMI, RI) and control over the frequency and method of their reporting, according to location, movement, and environment (urban/rural), while adapting to standard 3GPP channel models. The system is designed with a modular, Object-Oriented architecture, allowing researchers to effortlessly swap algorithms, introduce new models, and extract data securely (Data Validation) without compromising the core physics engine.

However, this is not a complete 5G network simulation. The simulation does not include a full implementation of the 5G **protocol stack**, and specifically does not simulate the **MAC**, **RLC**, and **PDCP** layers, full **scheduling** mechanisms, **HARQ**, **QoS** management, or **network slicing**. Furthermore, it does not include representation of the **5G Core Network**, including components such as **AMF**, **SMF**, and **UPF**, and there is no simulation of **end-to-end signaling** processes or **system-level latency**. Likewise, the simulation does not represent the behavior of a **commercial gNB** or a full implementation of **O-RAN** according to **3GPP** standards, but focuses only on channel modeling and algorithmic processes at the **PHY** and **RAN** levels.&nbsp;

---

## 

## **2\. System Requirements and Installation Instructions** {#2.-system-requirements-and-installation-instructions}

### **Prerequisites** {#prerequisites}

1. **MATLAB:** Version R2021a or newer (R2023b is recommended for optimal performance). The following Toolboxes are required:  
   * Communications Toolbox  
   * Phased Array System Toolbox (for antenna calculations)  
   * Statistics and Machine Learning Toolbox (for Voronoi and distribution calculations)  
2. **Quadriga:** Quadriga Channel Model library, version **2.8.1**.  
   * *Note:* Newer versions may change the *`qd_layout`* API and require code adjustments.  
3. **Hardware:** A computer with at least 16GB RAM is recommended (32GB is preferred for long runs) and a multi-core processor (for parallel computations in MATLAB).

### **Installation and Run Instructions** {#installation-and-run-instructions}

1. Download (Clone) the project code from [GitHub](https://github.com/Omri154/5G-Massive-MIMO-Simulator) to the local machine.  
2. Download the *`quadriga_src`* folder from the official [Quadriga website](https://quadriga-channel-model.de/) and extract it alongside the project folder (not inside it, to maintain order).  
3. Open MATLAB and navigate to the project folder.  
4. Add the Quadriga folder to the MATLAB Path:

*`addpath(genpath('../path_to_quadriga_folder'));`*

      5\. Run the command:

*`main_simulation`*

---

&nbsp;

## **3\. System Architecture** {#3.-system-architecture}

&nbsp;

The system is built on a modular architecture divided into 8 modules (folders) and one main entry file. This structure was chosen to separate the physics (Quadriga), the logic (time and motion management), and the data (Config).

&nbsp;

### **Entry Point \- mainSimulation.m** {#entry-point---mainsimulation.m-1}

This file orchestrates the complete program workflow:

* **Initialization:** Loads SimulationConfig.m and adds all subdirectories to the runtime path.  
* **Environment Generation:** Instantiates area, base station, and user generators utilizing predetermined Seeds to ensure reproducibility.  
* **Time Loop:** Advances the simulation clock in defined time steps (dt). In each step, the system:  
  * Updates UE positions and manages transitions between obscured/visible areas.  
  * Updates velocity vectors (in the random model).  
  * Generates CSI reports (including Handover logic and QuaDRiGa processing) at specified reporting intervals.  
* **Finalization and Storage:** Aggregates data from all components and passes it to ResultsManager.m for visualization and CSV storage.

Also, this file is managed in a smart way that makes the simulation run efficiently using the following mechanisms:

* **Memory Management:** Performs Pre-allocation of matrices for saving results. The required memory size is linear with respect to: NUEs X Nreports. For standard runs (100 users, 5 minutes), consumption is negligible (a few MB). For huge runs (millions of samples), the code must be changed to periodic writing to disk (Batch Writing) to avoid exceeding RAM.  
  The system pre-allocates memory for saving the results. To support dynamic CSI requests (where the number of reports is not known in advance) and huge runs without exceeding RAM, a **Buffer & Flush** mechanism will be implemented. A fixed-size buffer will be allocated (e.g., 10,000 reports). When the buffer is full, the data will be written sequentially (Append) to the disk file, and the buffer will be reset and overwritten. This ensures constant memory consumption throughout the simulation.  
* The simulation is based on absolute time (in seconds) and not on a number of iterations. It runs from moment 0 up to total\_duration. In each iteration, the simulation clock is advanced by a fixed step of position\_update\_dt (the movement resolution), which ensures continuous and physical updating of user locations.  
* **On-Demand CSI:** While the default is periodic reporting (according to csi\_report\_interval), the architecture allows for dynamic retrieval. External modules (such as a Scheduling server) will need to be built, capable of bypassing the periodic mechanism and calling the CSI extraction function for a specific user or group of users at any given moment on the timeline.

###### **The System Modules:** {#the-system-modules:}

The system is built on a modular architecture divided into 8 modules, allowing researchers to effortlessly swap algorithms, introduce new models, and extract data securely without compromising the core physics engine.

### **Module 1: Config** {#module-1:-config-1}

* **simulation\_config.m**: Centralizes all variable parameters.  
  * **Role:** The "brain" of the system. Returns a struct containing all parameters.  
  * **Details:** Defines the antenna configuration (MIMO 64x64 \- there are 64 transmitting and 64 receiving antennas, meaning 64 transmitters X 64 receivers), the size of the area, Seeds for randomness, and traffic and weather profiles. The code supports dynamic change (e.g., changing from 200x200 to 1000x1000 meters) without rewriting logic. (The data in the file itself can be changed, for example, changing from 8 polygons to 10 polygons, changing the area from 200x200 meters to 500x100, etc.).  
  * Also responsible for keeping the timestamp of the simulation run (can be changed to any desired date and time):&nbsp;  
    ![][image1]  
  * Additionally, this file contains traffic and weather profiles. That is, for each month, and for each type of region, the chance of rain and the intensity of the rain are defined according to the month (e.g., in January the chance of light rain is 0.3, the chance of heavy rain is 0.1, and otherwise, 0.6, there will be no rain). Similarly, the congestion level in a certain area is also defined according to the day and time (e.g., for a shopping center mid-week in the morning, the congestion factor will be 0.3, meaning medium-low, and for a shopping center on a weekend at noon, the congestion factor will be 0.9, meaning very high). The chances of rain and the congestion level were determined according to reality and can be changed if necessary.  
  * These settings are in the config file. For weather, these are probabilities, where the first number is the chance for comfortable weather without rain, the second number is the chance for light rain, and the third number is the chance for heavy rain. (The differences in weather are how much interference is added to the calculation of signal strength). Since these are probabilities, they must sum up to 1\.  
    Example of weather probabilities:

  ![][image2]

  * Regarding the congestion level, each area has 5 hour ranges. From midnight to six in the morning \- this is defined as night. From six in the morning to ten in the morning, this is defined as morning. From ten in the morning to five in the evening, this is defined as midday. From five in the evening to ten at night, this is defined as evening. And from ten at night to midnight, this is defined as late. The desired congestion level can be changed for each hour range. This must be a value between 0 and 1, where 0 means no congestion at all, and 1 means fully congested.  
    Example of congestion level definition according to a certain area by hours:			![][image4]

### **Module 2: Environment** {#module-2:-environment-1}

* **AreaGenerator.m**:  
  * **Role:** Creation of the area's topology.  
  * **Key Functions:**  
    * *`generate`*: Divides the area into polygons using Voronoi Tessellation.  
    * *`assign_matching_scenario`*: Attaches a suitable Quadriga profile to each area (e.g., Shopping Center receives 3GPP\_38.901\_UMi\_NLOS).

Example of an area divided into polygons using Voronoi:&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

* What are the Quadriga profiles?  
  Quadriga profiles (or scenarios, as they are called in Quadriga) are the physical definitions of the type of region that Quadriga will randomly select and assign to that area. The scenario is defined by the type of environment (urban micro/urban macro/rural macro/indoor hotspot) and line of sight (LOS \- line of sight/NLOS \- non line of sight). In practice, these profiles affect the mathematical calculations and the stochasticity of the scenario:  
  When a profile is defined, QuaDRiGa loads a set of statistical parameters (LSP \- Large Scale Parameters) that directly influence:  
  1. **Path Loss Formula:** The formula that calculates how much attenuation there is per distance (e.g., in RMa the attenuation will be proportional to d2, while in UMi\_NLOS it will be close to d3.5).  
  2. **Delay Spread:** The time gap between the arrival of the first and last ray (larger in cities due to distant reflections).  
  3. **Angular Spread:** How much the rays are "spread" in space (critical for MIMO and Beamforming calculations).  
  4. **Number of Clusters:** How many "clusters of reflections" (walls, buildings) the software randomly generates around the user.

### **Module 3: Mobility** {#module-3:-mobility-1}

Manages UE movement across the geographical space. The system supports two primary, interchangeable models:

* **Random walk mobility model \- RandomWalkModel.m**:  
  * **Role:** The physics engine for user movement.  
  * **Logic:** A "billiard" model \- every user moves in a straight line, changes direction and speed every X seconds, and performs a Reflection when colliding with the map boundaries.  
  * Example of paths for 35 users over 90 seconds:  
    &nbsp;

&nbsp;

* To create a model of specific places (e.g., work/home/school, etc.), the area will be converted into a graph with points of interest as the nodes, and roads and sidewalks as the edges. (MATLAB already implemented objects for creating graphs). Then, using Dijkstra's or a shortest path algorithm, the user will be advanced along that path toward the point they need to reach in the end.  
  * Regarding the issue of a group of users moving together, a known solution used is RPGM (Reference Point Group Mobility). For example, for a group of 3 users, one of the users will be set as the leader who will actually advance on the map, and for the other two, a deviation of half a meter, for instance, from the leader will be added, and their channel will be calculated according to that location.  
* **Trace-Based Mobility Model \- TraceBasedModel.m:**  
  * This model enables deterministic UE movement driven by external CSV trajectory files.  
  * **Data Structure:** Utilizes a "Long Format" CSV input where each record defines a UE waypoint with (x, y) coordinates and a departure timestamp. The system supports a heterogeneous number of waypoints per UE.  
  * Example of a valid input file:&nbsp;  
    When entering the departure time, the full time must be entered, including seconds. (Excel displays a short time format, so the seconds are not displayed here).  
  * **Interpolation Logic:** Positions are calculated using real-time linear interpolation between waypoints. Velocity is strictly derived from the distance and time duration between points, ensuring physical consistency for Doppler effect calculations.  
  * **Stateful Implementation:** The model is designed as a handle object that tracks the current segment index for each UE. This ensures O(1) computational complexity during simulation steps, avoiding redundant data scans.  
  * **Robustness:** Includes automated validation of implied physical speeds and provides stationary fallback trajectories for UEs missing from the input trace file.  
  * Example of users movement using the new model:&nbsp;  
    The image shows 15 users, each of whom goes from point A to point B and returns to point A (as shown in the input file specific to this run).

&nbsp;

&nbsp;

&nbsp;

### **Module 4: Network** {#module-4:-network-1}

* **BaseStationManager.m**:  
  * **Role:** Management of Base Stations (BS).  
  * **Key Functions:** Creates **Massive MIMO 8x8** antenna arrays (i.e., 64 elements) in a Cross-Polarized configuration, including control over direction (Azimuth) and tilt (Downtilt).  
* **UserEquipmentManager.m**:  
  * **Role:** Management of User Equipment (UEs).  
  * **Key Functions:** Synchronizes the user's physical location (from the Mobility module) with the antenna object in Quadriga.

### **Module 5: Simulation** {#module-5:-simulation-1}

This module contains the simulation's "engines".

* **CSIReporter.m**:  
  * **Role:** The interface with Quadriga. This version underwent massive optimization.  
  * **Innovation:** Instead of calculating the channel for each user separately, it groups users by area and BS and runs **one call** (Batch) to Quadriga.  
  * **Context:** Adds the effects of weather and load on the raw data.  
  * **Smart Base Station Selection (Handover Mechanism):** To realistically simulate the Handover process and prevent naive geometric-only associations, a two-phase architecture is implemented within the simulator:  
    * **Heuristic Selection Phase:** The *`find_serving_bs`* function handles cell selection. It evaluates the RSRP for all base stations based on Free Space Path Loss (FSPL) combined with a deterministic Cross-Area Propagation Penalty. The logic weighs the endpoint environment scenarios (LOS/NLOS) of both the UE and the BS. If the signal path crosses obscured areas, a penalty (up to 15dB) is applied to reflect physical obstacles (buildings, dense environments). This mechanism smartly allows a UE to connect to a geographically further BS if it offers a clearer Line-of-Sight (LOS).  
    * **Physical Evaluation Phase:** Once the Serving BS is decided in phase 1, the connection mapping is passed to the QuaDRiGa engine. Here, the exact physical channel (CSI, SINR, RSRP, CQI) is rigorously calculated using statistical ray-tracing. The heuristic penalty from phase 1 is purely for connection decision-making and is strictly excluded from the final physics calculations, preventing any "double penalty" data distortion.  
* **TimeManager.m**:  
  * **Role:** Management of the simulation clock.  
  * **Logic:** Manages accurate time counters to determine when to update location (every 0.1s) and when to generate a CSI report (every 0.5s), while preventing Floating Point Drift errors.  
* **TransitionManager.m**:  
  * **Role:** Handling transitions between areas.  
  * **Logic:** Calculates a *`blend_factor`* to allow a smooth transition of the communication channel when a user crosses a boundary between two Voronoi areas.  
  * **The Transition Mechanism and *blend\_factor* Calculation:** In the real world, moving from one geographic area to another (e.g., exiting a dense neighborhood onto an open road) does not cause an immediate and sharp jump in Received Signal Reference Power (RSRP) or signal quality. To simulate this, the TransitionManager defines "Transition Zones" between the Voronoi polygons.  
  * **How it works?** The logic finds the two closest Seeds for each user. If the difference between the distances to the two seeds is smaller than a pre-defined parameter (*`transition_width`*) (currently the *`transition_width`* is defined as 10 meters), the system identifies that the user is in the transition zone.  
  * **What is the *blend\_factor*?** This is a coefficient (between 0 and 1\) representing the "weight" of the user's proximity to each of the two areas. A coefficient of 0.5 means the user is exactly on the theoretical boundary line.  
  * **What does it affect?** The *`blend_factor`* is used by the *`CSI_Reporter`* to perform interpolation (weighted averaging) between the channel characteristics of area A and the characteristics of area B. This operation ensures a smooth and continuous fade or strengthening of the CSI metrics, and prevents "artificial noise" and illogical jumps in the Dataset that will be used by the ML model.

### **Module 6: Output** {#module-6:-output-1}

* **ResultsManager.m**:  
  * **Role:** Responsible for data aggregation, processing, and visualization  
  * **Outputs:** Saves CSV files (one for each user \+ a centralized file), and automatically generates a set of 8 graphs for performance analysis (heatmaps, SINR distribution, movement paths, etc.).

### **Module 7: Tests** {#module-7:-tests-1}

Contains Unit Tests and scripts for verifying the integrity of the different modules before a full run.

&nbsp;

**What is checked in these tests?** These tests are intended to ensure that each module functions properly independently, before integrating it into the main engine.

* **Mobility Tests:** Verify that users do not exit the map boundaries (checking the Reflection mechanism at the walls) and that the randomly generated speeds remain within the allowed minimum and maximum limits.  
* **Geometry Tests:** Verify that the Voronoi algorithm and the area finding function (Nearest Neighbor) assign every coordinate to the correct area with 100% accuracy.  
* **Network Manager Tests (BS/UE Managers):** Verify that the QuaDRiGa objects are successfully created, and that the antenna arrays indeed contain the exact number of elements defined in the configuration (e.g., verifying the creation of 64 physical elements for each base station).

### **Module 8: Utils** {#module-8:-utils-1}

Reusable utility libraries.

* **GeometryUtils.m**: Calculations for distance, angles, and finding the closest area.  
* **TrafficUtils.m**: Calculation of network load (0-1) according to the time of day and area type (e.g., an office busy in the morning and empty at night).  
* **WeatherUtils.m**: Conversion of date to rain probability, and calculation of Attenuation according to the ITU-R model.  
* **ValidationUtils.m**: Assertions to prevent running the simulation with incorrect parameters.  
  This file acts as the simulation's "gatekeeper," performing a series of critical tests (Assertions) divided into two main stages:  
1. **Pre-Run Tests (Config Validation):** Before the simulation begins, the code checks that the Config file is physically sensible.  
   * Verification that the area dimensions (*`area_width`* and *`area_height`*) are positive.  
   * Verification that the number of Voronoi areas is reasonable (between 2 and 20 areas).  
   * Verification that there is at least one Base Station (BS) and one User Equipment (UE), and that all have at least one transmitting (Tx) and one receiving (Rx) antenna.  
2. **Post-Run Tests (CSI Metrics Validation):** At the end of the simulation, quality control is performed on the generated data to ensure the Dataset is valid for Machine Learning.  
   * The code summarizes the number of reports actually created versus the expected number.  
   * It examines the calculated RSRP and SINR values and verifies that they fall within sensible physical Ranges. The system checks minimum and maximum values and calculates averages to ensure there are no anomalies like NaN or Inf values that might result from division by zero in empty areas.  
* **`GenerateTestCSV.m`:** Generates a sample CSV file for running the trace-based mobility model according to the number of UEs defined in the config file, within the directory specified in the config file. By default, the file is created inside the 'data' directory under the main project root. The destination folder can be changed in the configuration file:&nbsp;

---

## 

## **4\. Simulation Control (Configuration)** {#4.-simulation-control-(configuration)}

&nbsp;

All control is done through the *`simulation_config.m`* file.  
There is no need to change code in the other modules.

&nbsp;

**Main Parameters to Change:**

1. **Seeds:**  
   * *`random_seed_areas`*: Determines the map shape (Voronoi division).  
   * *`random_seed_mobility`*: Determines the user movement paths (in the random walk model).  
2. **Time:**  
   * *`simulation_datetime`*: Determines the season (rain) and the hour (load).  
   * *`total_duration`*: The length of the simulation in seconds.  
3. **Network:**  
   * *`ue.num`*: Number of users.  
   * *`bs.num_tx`*: Number of antennas per BS (defined as 64).  
4. **Mobility:**  
   To switch between the different mobility models, the required changes are:&nbsp;  
   * Switching from the trace-based mobility model to the random walk model:  
     In *`config.mobility.model:`* change from 'trace\_based' to 'random\_walk' for the random walk model.  
   * Switching from the random walk model to the trace-based mobility model:  
     In *`config.mobility.model:`* change from 'random\_walk' to 'trace\_based' for the trace-based model. It is just important to ensure there is a properly formatted input file inside the data directory, as in the following example:

---

## **5\. Running the Simulation** {#5.-running-the-simulation}

&nbsp;

To run the simulation and obtain the data:

1. Open the main folder in MATLAB.  
2. Run the command: *`main_simulation`*  
3. **What happens during the run?**  
   * The system will initialize all modules.  
   * The expected Memory Allocation will be printed.  
   * The time loop will run and print a progress status every 30 seconds.  
4. **Upon completion of the run:**  
   * A new folder will open under *`results/simulation_YYYYMMDD_HHMMSS`.*  
   * The CSV files will be saved in the *`csv`* folder.  
   * The graphs will be saved in the *`figures`* folder.  
   * A summary HTML report will open in the browser.

---

## 

## **6\. Future Additions and Improvements** {#6.-future-additions-and-improvements}

This section is intended for researchers and developers continuing work on the project. It includes architectural planning for improvements that were deferred in order to achieve functional stability.&nbsp;

### **Recommended Future Improvements and Developments:**&nbsp;

1. **Increasing Heterogeneity in User Antenna Arrays:**  
   **Problem Description:** In the current version, within the *`run_quadriga_batch`* function (in the CSIReporter.m file), the assignment *`layout.rx_array = rx_arrays{1}`* causes all users (UEs) in the batch to receive only the radiation pattern and antenna array of the first user. This eliminates the Spatial Diversity between different devices (e.g., 4x4 MIMO vs. 1x1 SISO).  
   **Planned Fix:** The QuaDRiGa engine can accept a full Cell Array. The assignment should be changed to *`layout.rx_array = rx_arrays;`*. It is important to ensure that the User Manager indeed allocates antennas with different orientations or a different number of elements to each UE. This can be done by adding the desired antenna array for each UE alongside its starting point in the input file of the new mobility model.  
2. **Asynchronous Velocity Updates for Users:**  
   **Problem Description:** When using the random mobility model (RandomWalkModel), the *`time_manager.should_update_velocities()`* function in the main loop causes all users in the simulation to change direction and speed at the exact same second (e.g., every 10 seconds). This creates an artificial movement pattern.  
   **Planned Fix:** Move the velocity update timer into the UE object itself. Each user will hold an internal variable *`time_to_next_turn`*, which will receive a random value upon its creation. The velocity update will occur independently for each user according to their private clock.  
3. **Optimization and Caching for Base Station Selection:**  
   **Problem Description:** The *`find_serving_bs`* function performs intensive computational work during every CSI reporting event (every half second). In practice, cellular users do not change base stations at such a frequency.  
   **Planned Fix:** Add a Cache for each user. The system will search for a new base station only if the UE has crossed a zone boundary (Voronoi Border), or if X seconds/meters have passed since the last Handover calculation. This will drastically reduce the simulation runtime.  
4. **Advanced Inter-Polygon Transition Logic:**  
   **Problem Description:** In the TransitionManager module, the current logic handles transitions between exactly two areas (area\_pair(2)). In an edge case where a user moves exactly over a vertex shared by three (or more) Voronoi cells, the influence of the third area is ignored.  
   **Planned Fix:** Expand the algorithm so that it returns an array of weights for all adjacent areas based on their Euclidean distance from the user's point, and average the channel parameters (Blend) across all of them.  
   &nbsp;  
5. **Flexibility in the Weather Model:**  
   **Problem Description:** In the WeatherUtils.m file, there is a hardcoded implementation of weather (which is currently set to the Mediterranean weather of Israel).  
   \*There is also a check that forces no rain in July/August, and if the weather is changed to another profile, for example a southern one like Australia, where summer rain is common, the system will necessarily alter it so that the summer months remain dry.  
   **Planned Fix:** Expose the weather type and rain intensity (mm/hr) as dynamic parameters in the SimulationConfig.m file, or fetch them from a historical meteorological dataset synchronized with the system's timeline.

---

## 

## **7\. Technical Summary** {#7.-technical-summary}

The current simulation represents the State-of-the-Art in using Quadriga for Data generation. The combination of **Massive MIMO**, **Batch Processing** in the CSI Reporter, and **Context** management (time/weather) ensures that the produced data will be realistic, diverse, and suitable for advanced research.

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

---

## **8\. Example Results** {#8.-example-results}

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

**Example of some of UE No. 1's reports:**

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>