# **Sign Language Interactive System – Telegram Bot**

## **Project Overview**

This project aims to bridge communication barriers for the **deaf and hard-of-hearing community** through a **Telegram-based sign language translation and learning platform**. The bot enables **sign language recognition, structured learning, and real-time interaction** with translators and instructors.

### **Key Features:**

- **Sign Language Video Upload & Translation** – Users submit sign language videos, and translators provide feedback.
- **Structured Learning System** – Teachers create **video-based lessons**, and students replicate and receive feedback.
- **Voting & Ranking System** – Translators and teachers **evaluate contributions** to ensure high-quality translations.
- **Admin Panel for Management** – Enables **user moderation, classroom control, and report handling**.
- **Classroom Functionality** - Users can join structured **classrooms** where teachers provide lessons, assign practice videos, and evaluate students' progress.
- **Multi-Language Support** – Supports **Russian, Ukrainian, and Azerbaijani** sign languages, with plans for **cross-sign-language translation** (ASL → RSL).

---

## **Project Structure**

```
├── bot/
│   ├── main.py                     # Main bot entry point
│   ├── database_service.py          # Handles PostgreSQL interactions
│   ├── registration_handlers.py     # Manages user registration flow
│   ├── translation_manager.py       # Handles sign language translation process
│   ├── user_handlers.py             # Processes user interactions & feedback
│   ├── classroom_module.py          # Manages classroom functionalities (teachers, students)
│   ├── admin_panel.py               # Admin control panel for moderation & reporting
│   ├── voting_system.py             # Voting and ranking logic for translators and users
│   ├── feedback_system.py           # Enables translator feedback for users
│   ├── config.py                    # Configuration settings (API keys, database)
│   ├── utils.py                      # Helper functions for bot interactions
│
├── models/
│   ├── mediapipe_model.py           # Real-time sign language recognition
│   ├── sign_language_model.py       # AI model for gesture-based text conversion
│
├── datasets/
│   ├── user_videos/                 # User-submitted videos
│   ├── translator_videos/           # Verified translator-provided videos
│
├── api/
│   ├── server.py                     # API server for processing translations
│   ├── endpoints.py                   # API endpoints for bot interactions
│
├── docs/
│   ├── architecture.md               # Technical documentation of system design
│   ├── database_schema.md            # Database ERD & schema details
│   ├── user_guide.md                 # User manual for bot interaction
│
├── requirements.txt                  # List of dependencies
├── README.md                         # Project documentation
├── config.yaml                        # Configuration file for deployment
```

---

## **Installation & Setup**

### **1. Prerequisites**

Ensure you have:
- **Python 3.8+** installed
- **PostgreSQL database** running
- **Telegram Bot API token**

### **2. Clone the Repository**

```bash
git clone https://github.com/ElvinKarayev/Sign_Language_System.git
cd Sign_Language_System
```

### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **4. Configure Environment**

Create a `.env` file and add your API keys:

```env
TELEGRAM_BOT_TOKEN=your_token_here
DATABASE_URL=postgres://user:password@host:port/dbname
```

### **5. Run the Bot**

```bash
python bot/main.py
```

---

## **System Architecture**

### **Architecture Flow:**

1. **User uploads a sign language video** via the Telegram bot.
2. **Translation request is sent to human translators** for verification.
3.  **Translators review and provide feedback** (ranking & comments).
4.**Users receive translations & learning resources**.

### **Technologies Used:**

- **Python** – Core bot logic
- **PostgreSQL** – Database for storing users, translations, and rankings
- **Spring Boot (Planned for Admin Panel)** – Web-based management interface

---

## **Translator Incentive System**

To **attract and retain skilled translators**, we have implemented a **performance-based payment system**.

### **Reward Tiers:**

- **Top 5% of translators** → **150 AZN each**
- **Next 10% (excluding Top 5%)** → **100 AZN each**
- **Next 15% (excluding Top 5% and 10%)** → **50 AZN each**

---

## **Future Enhancements**

- **Admin Panel (Spring Boot-based UI)**
- **Real-Time AI Sign Language Translation** (Live sign-to-text conversion)
- **ASAN Center Deployment** (Government service integration)
- **Cross-Sign Language Translation** (ASL → Russian Sign Language)
- **Advanced Gesture Detection with MediaPipe**

---


