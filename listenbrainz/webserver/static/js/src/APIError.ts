export default class APIError extends Error {
  status?: string;

  response?: Response;
}
