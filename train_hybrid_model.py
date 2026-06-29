import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

# LOAD DATA
real_df = pd.read_csv("sensor_data.csv")
real_df.columns = ['temp','hum','pressure','mq2','mq135','label']

real_df['aqi']=(real_df['mq135']/1023)*500
real_df['gas_ratio']=real_df['mq2']/(real_df['mq135']+1)

online_df = pd.read_csv("Gas_Sensors_Measurements.csv")
online_df = online_df.rename(columns={'MQ2':'mq2','MQ135':'mq135','Gas':'label'})
online_df = online_df[['mq2','mq135','label']]

def fix(x):
    x=str(x).lower()
    if 'smoke' in x: return "Severe Smoke"
    elif 'lpg' in x or 'gas' in x: return "Gas Danger"
    elif 'co' in x: return "High Pollution"
    else: return "Safe"

online_df['label']=online_df['label'].apply(fix)

online_df['temp']=30
online_df['hum']=60
online_df['pressure']=1013

online_df['aqi']=(online_df['mq135']/1023)*500
online_df['gas_ratio']=online_df['mq2']/(online_df['mq135']+1)

df=pd.concat([real_df,online_df])

X=df[['temp','hum','pressure','mq2','mq135','aqi','gas_ratio']]
y=df['label']

X_train,X_test,y_train,y_test=train_test_split(
    X,y,test_size=0.2,random_state=42,stratify=y
)

model=RandomForestClassifier(n_estimators=600,max_depth=18)
model.fit(X_train,y_train)

y_pred=model.predict(X_test)

print("🔥 Accuracy:",accuracy_score(y_test,y_pred))
print("\n📊 Report:\n",classification_report(y_test,y_pred))

joblib.dump(model,"env_ai_model2.pkl")