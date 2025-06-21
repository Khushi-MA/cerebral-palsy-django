### **Project Title:**

**Role-Based Hospital Management System for Cerebral Palsy Patient Data** *(DBMS Project implemented using Django)*

### **Project Overview:**

This project is a **Database Management System (DBMS)** designed to handle **structured medical data** for **cerebral palsy patients**, implemented through the Django web framework. The system focuses on **data organization, secure access control, and hierarchical user role management** to ensure reliable handling of patient records.

The core of the system is a **centralized relational database** that manages entities such as **Hospitals, Doctors, Patients, and Visit Records**. The project enforces **role-based access control (RBAC)** to protect sensitive medical data while enabling collaboration among medical professionals.

---

### **Key Features:**

* **Data Centralization:**
  A structured, normalized database schema is used to store patient records, visit histories, and sensor data, ensuring data consistency and minimizing redundancy.

* **Entity Relationships:**
  The system defines clear **1-to-many** and **many-to-1** relationships:

  * One Admin → Many Hospitals
  * One Hospital → Many Doctors
  * One Doctor → Many Patients
  * One Patient → Many Visits
  * Each Visit → Contains sensor data and diagnosis notes

* **Role-Based Access Control (RBAC):**
  Access to the database is restricted based on user roles (Admin, Hospital, Doctor). Each role has well-defined **permissions** on database entities, implemented via Django’s ORM (Object-Relational Mapping) and middleware.

* **Data Integrity and Auditability:**
  Constraints such as **foreign keys, uniqueness, and cascading deletes** ensure data integrity. Additionally, Django models are structured to maintain timestamped logs for visits and updates, supporting traceability of patient care.

* **Collaborative Access Logic:**

  * **Primary Doctor**: Full CRUD access to their assigned patient’s records.
  * **Secondary Doctor**: Editable access to patients they're assigned to as secondary.
  * **Other Doctors in the Hospital**: Read-only access to all patient data within their hospital.
  * **Admin and Hospital Managers**: Read-only access to all data under their hierarchy.

* **Sensor Data Handling:**
  Medical sensor readings are stored as structured data in NumPy format, linked via database fields to patient visit records, ensuring advanced data storage and retrieval capability.

---

### **Database Schema Overview:**

| Table        | Key Fields                                                           | Relationships                                  |
| ------------ | -------------------------------------------------------------------- | ---------------------------------------------- |
| `Admin`      | id, name, email                                                      | Has many `Hospitals`                           |
| `Hospital`   | id, name, admin\_id (FK)                                             | Has many `Doctors`                             |
| `Doctor`     | id, name, hospital\_id (FK), role (primary/secondary)                | Has many `Patients` (as primary), views others |
| `Patient`    | id, name, primary\_doctor\_id (FK), secondary\_doctor\_id (nullable) | Has many `Visits`                              |
| `Visit`      | id, patient\_id (FK), doctor\_id (FK), timestamp, notes              | One visit per patient-doctor session           |
| `SensorData` | id, visit\_id (FK), file\_path (.npy), created\_at                   | One-to-one or one-to-many with `Visit`         |

---

### **System Roles and Permissions (DBMS View):**

| **ROLE**     | **DB ACCESS & PERMISSIONS**                                                                 |
| ------------ | ------------------------------------------------------------------------------------------- |
| **Admin**    | Full read access to all tables. Can insert/update/delete `Hospital` records.                |
| **Hospital** | Can read all `Doctor` and `Patient` records under their hospital. Can insert `Doctor`.      |
| **Doctor**   | Can insert/update `Patient` and `Visit` records for their assigned patients. View all data. |
| **Patient**  | Not a database user. Their records are created and maintained via `Doctor` operations.      |

---

### **Implementation Details:**

* **Backend Framework:** Django (Python)
* **Database Engine:** SQLite (dev) / PostgreSQL (prod-ready)
* **Frontend:** Django Templates (HTML/CSS/JS)
* **ORM:** Django Models manage database tables and relations.
* **Security:** Role-based middleware, login sessions, and model-level permission checks.
