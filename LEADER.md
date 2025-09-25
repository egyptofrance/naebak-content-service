# 📝 LEADER - دليل خدمة المحتوى (Content Service)

**اسم الخدمة:** naebak-content-service  
**المنفذ:** 8010  
**الإطار:** Flask 2.3  
**قاعدة البيانات:** SQLite  
**النوع:** Content Management (إدارة المحتوى)  

---

## 📋 **نظرة عامة على الخدمة**

### **🎯 الغرض الأساسي:**
خدمة المحتوى هي المسؤولة عن إدارة وتوفير المحتوى الثابت والديناميكي في منصة نائبك. هذا يشمل الصفحات التعريفية (من نحن، سياسة الخصوصية)، المقالات، الأسئلة الشائعة، وأي محتوى آخر يتم عرضه للمستخدمين.

### **📝 كيف يعمل التطبيق بالضبط:**

**للمطور - فهم إدارة المحتوى:**
1. **تخزين المحتوى:** يتم تخزين المحتوى في قاعدة بيانات SQLite الخاصة بالخدمة.
2. **واجهة برمجة التطبيقات (API):** توفر الخدمة واجهة برمجة تطبيقات (API) للوصول إلى المحتوى.
3. **التكامل مع البوابة:** يتم توجيه جميع الطلبات إلى خدمة المحتوى عبر البوابة (Gateway).

**للأدمن - إدارة المحتوى:**
1. **لوحة التحكم:** يستخدم الأدمن لوحة تحكم خاصة (عبر خدمة الإدارة) لتعديل المحتوى.
2. **تحديث المحتوى:** يمكن للأدمن إضافة، تعديل، أو حذف أي محتوى.
3. **التحديث الفوري:** تظهر التغييرات على الفور في المنصة.

**مثال عملي:**
```
الأدمن يريد تعديل صفحة "من نحن"
↓
يدخل إلى لوحة التحكم ويختار صفحة "من نحن"
↓
يعدل النص ويحفظ التغييرات
↓
خدمة الإدارة ترسل طلبًا إلى خدمة المحتوى لتحديث الصفحة
↓
خدمة المحتوى تحدث قاعدة بياناتها
↓
أي مستخدم يزور صفحة "من نحن" يرى المحتوى المحدث
```

---

## 🌐 **دور الخدمة في منصة نائبك**

### **🏛️ المكانة في النظام:**
خدمة المحتوى هي **المصدر الأساسي للمعلومات** في المنصة، حيث توفر المحتوى الذي يقرأه المستخدمون ويتفاعلون معه.

### **📡 العلاقات مع الخدمات الأخرى:**

#### **🔗 الخدمات المرتبطة:**
- **خدمة البوابة (Gateway):** توجه الطلبات إلى خدمة المحتوى.
- **خدمة الإدارة (Admin Service):** توفر واجهة لإدارة المحتوى.

---

## 📊 **البيانات الأساسية**

### **📝 نماذج البيانات:**
```python
# نموذج لصفحة محتوى
class ContentPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'about-us'
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

# نموذج لمقالة
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    publish_date = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## ⚙️ **إعدادات Google Cloud Run**

### **🔧 بيئة التطوير:**
```yaml
Environment: development
Port: 8010
Database: SQLite (local file)
Resources:
  CPU: 0.2
  Memory: 128Mi
  Max Instances: 1

Environment Variables:
  FLASK_ENV=development
  DATABASE_URL=sqlite:///content.db
  DEBUG=true
```

### **🚀 بيئة الإنتاج:**
```yaml
Environment: production
Port: 8010
Database: SQLite (persistent volume)
Resources:
  CPU: 0.3
  Memory: 256Mi
  Max Instances: 5
  Min Instances: 1

Environment Variables:
  FLASK_ENV=production
  DATABASE_URL=sqlite:///data/content.db
  DEBUG=false
```

