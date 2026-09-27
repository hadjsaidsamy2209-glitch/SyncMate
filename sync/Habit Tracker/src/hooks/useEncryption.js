import CryptoJS from 'crypto-js';

const SECRET_KEY = 'HabitTrackerApp2026_SecretKey_32Chars!!';

const encryptField = (value) => {
  return CryptoJS.AES.encrypt(JSON.stringify(value), SECRET_KEY).toString();
};

const decryptField = (encrypted) => {
  try {
    return JSON.parse(CryptoJS.AES.decrypt(encrypted, SECRET_KEY).toString(CryptoJS.enc.Utf8));
  } catch {
    return encrypted; // Fallback si erreur
  }
};

export const encryptHabit = (habit) => {
  const result = {};
  if (habit.name !== undefined) result.name = encryptField(habit.name);
  if (habit.completed !== undefined) result.completed = encryptField(habit.completed);
  if (habit.history !== undefined) result.history = encryptField(habit.history || []);
  if (habit.streak !== undefined) result.streak = encryptField(habit.streak || 0);
  if (habit.bestStreak !== undefined) result.bestStreak = encryptField(habit.bestStreak || 0);
  if (habit.createdAt !== undefined) result.createdAt = encryptField(habit.createdAt);
  return result;
};

export const decryptHabit = (encryptedHabit) => ({
  ...encryptedHabit,
  name: decryptField(encryptedHabit.name),
  completed: decryptField(encryptedHabit.completed),
  history: decryptField(encryptedHabit.history),
  streak: parseInt(decryptField(encryptedHabit.streak)) || 0,
  bestStreak: parseInt(decryptField(encryptedHabit.bestStreak)) || 0,
  createdAt: decryptField(encryptedHabit.createdAt),
});

export const decryptHabits = (habits) => habits.map(decryptHabit);