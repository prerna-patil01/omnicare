import { api, unwrap } from "@/lib/api";

/** Doctors, care services, appointments, rides, and pharmacy. */

export const fetchDoctors = (params = {}) => unwrap(api.get("/doctors", { params }));

export const fetchCareServices = () => unwrap(api.get("/care-services"));

export const fetchAppointments = () => unwrap(api.get("/appointments"));

export const bookAppointment = (doctorId, mode = "in_person") =>
  unwrap(api.post("/appointments", { doctorId, mode }));

export const cancelAppointment = (appointmentId) =>
  unwrap(api.post(`/appointments/${appointmentId}/cancel`));

export const fetchRideOptions = (appointmentId) =>
  unwrap(api.get(`/appointments/${appointmentId}/rides`));

export const fetchMedicines = (params = {}) =>
  unwrap(api.get("/pharmacy/medicines", { params }));

export const fetchCart = () => unwrap(api.get("/pharmacy/cart"));

export const addToCart = (medicineId, quantity = 1) =>
  unwrap(api.post("/pharmacy/cart", { medicineId, quantity }));

export const updateCartItem = (itemId, quantity) =>
  unwrap(api.patch(`/pharmacy/cart/${itemId}`, { quantity }));

export const removeCartItem = (itemId) => unwrap(api.delete(`/pharmacy/cart/${itemId}`));

export const checkout = (address) => unwrap(api.post("/pharmacy/checkout", { address }));
