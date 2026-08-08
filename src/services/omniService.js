import { api, unwrap } from "@/lib/api";

/** Ask Omni — conversations and the deliberation turn. */

export const fetchConversations = () => unwrap(api.get("/omni/conversations"));

export const createConversation = () => unwrap(api.post("/omni/conversations"));

export const fetchConversation = (conversationId) =>
  unwrap(api.get(`/omni/conversations/${conversationId}`));

export const sendMessage = (conversationId, body) =>
  unwrap(api.post(`/omni/conversations/${conversationId}/messages`, { body }));

export const deleteConversation = (conversationId) =>
  unwrap(api.delete(`/omni/conversations/${conversationId}`));
