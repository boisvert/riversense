import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

# Step 1: Connect to the SQLite database and retrieve the data
def fetch_data_from_db(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT created_at, temperature, percent_dissolved_oxygen FROM SensorData')  # Fetch created_at
        rows = cursor.fetchall()
        conn.close()
        return np.array(rows)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

# Step 2: Label data as 'fine' or 'defected' based on the logic
def label_data(temperature, percent_do):
    labels = np.zeros(len(temperature))
    for i in range(len(temperature)):
        if (temperature[i] > 30 and percent_do[i] < 30) or (temperature[i] < 20 and percent_do[i] > 70):
            labels[i] = 0  # Fine data
        else:
            labels[i] = 1  # Defected data
    return labels

# Step 3: Create a CNN Model with reduced complexity and higher dropout
def create_cnn_model(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape),
        tf.keras.layers.Conv1D(filters=8, kernel_size=1, activation='relu'),  # Reduced filters further
        tf.keras.layers.MaxPooling1D(pool_size=1),
        tf.keras.layers.Dropout(0.4),  # Increased dropout rate to 40%
        tf.keras.layers.Conv1D(filters=16, kernel_size=1, activation='relu'),  # Reduced filters
        tf.keras.layers.MaxPooling1D(pool_size=1),
        tf.keras.layers.Dropout(0.4),  # Increased dropout rate
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(16, activation='relu'),  # Further reduced dense units
        tf.keras.layers.Dropout(0.4),  # Dropout before final layer
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# Step 4: Plot Line Graph for Defected Data with Respect to created_at (timestamp)
def plot_defected_data(created_at, temperature, percent_do, labels):
    # Filter defected data (labels == 1)
    defected_indices = np.where(labels == 1)[0]
    defected_created_at = created_at[defected_indices]
    defected_temperature = temperature[defected_indices]
    defected_percent_do = percent_do[defected_indices]

    plt.figure(figsize=(12, 6))
    plt.plot(defected_created_at, defected_temperature, label='Temperature (°C)', color='r', marker='o')
    plt.plot(defected_created_at, defected_percent_do, label='Percent Dissolved Oxygen (%)', color='b', marker='x')
    plt.xlabel('Timestamp (created_at)')
    plt.ylabel('Values')
    plt.title('Defected Data: Temperature and Percent Dissolved Oxygen Over Time')
    plt.xticks(rotation=45)  # Rotate created_at labels for better readability
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.show()

# Step 5: Main function for fetching data, training the model, and visualizing results
def main():
    db_file = "aqua_sensor_data121.db"  # Replace with your actual database path
    
    # Fetch created_at, temperature, and dissolved oxygen data from the database
    data = fetch_data_from_db(db_file)
    if data is None:
        return
    
    # Split the data into created_at, temperature, and percent_dissolved_oxygen arrays
    created_at = data[:, 0]
    temperature = data[:, 1].astype(float)  # Ensure temperature is in float format
    percent_do = data[:, 2].astype(float)  # Ensure percent dissolved oxygen is in float format
    
    # Label the data as 'fine' or 'defected' based on the logic
    labels = label_data(temperature, percent_do)
    
    # Plot the defected data with respect to created_at
    plot_defected_data(created_at, temperature, percent_do, labels)
    
    # Combine temperature and percent_dissolved_oxygen into a 2D feature set
    X = np.vstack((temperature, percent_do)).T

    # Shuffle data to avoid any bias from data order
    X, labels = shuffle(X, labels, random_state=42)

    # Increase the noise factor to make the task harder
    noise_factor = 0.05  # Increased noise factor to 5%
    X_noisy = X + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=X.shape)

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X_noisy, labels, test_size=0.3, random_state=42)

    # Reshape data for CNN input (CNN expects 3D input)
    X_train_reshaped = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
    X_test_reshaped = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))

    # Print the shape to verify the dimensions
    print(f"X_train_reshaped shape: {X_train_reshaped.shape}")
    print(f"X_test_reshaped shape: {X_test_reshaped.shape}")

    # Create and compile the model
    model = create_cnn_model((X_train_reshaped.shape[1], 1))

    # Train the model with fewer epochs to avoid overfitting
    history = model.fit(X_train_reshaped, y_train, epochs=10, validation_data=(X_test_reshaped, y_test))

    # Step 6: Plot Training and Validation Accuracy
    plt.plot(history.history['accuracy'], label='Train Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.title('Model Accuracy')
    plt.legend()
    plt.show()

    # Step 7: Evaluate the model
    loss, accuracy = model.evaluate(X_test_reshaped, y_test)
    print(f"Test Accuracy: {accuracy*100:.2f}%")

    # Step 8: Predict and plot results
    y_pred = (model.predict(X_test_reshaped) > 0.5).astype("int32")

    # Visualization of fine vs defected data
    plt.figure(figsize=(10, 6))
    plt.scatter(temperature[labels == 0], percent_do[labels == 0], color='green', label='Fine Data')
    plt.scatter(temperature[labels == 1], percent_do[labels == 1], color='red', label='Defected Data')
    plt.xlabel('Temperature (°C)')
    plt.ylabel('Percent Dissolved Oxygen (%)')
    plt.title('Fine vs Defected Data')
    plt.legend()
    plt.show()

if __name__ == "__main__":
    main()
