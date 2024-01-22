// Mocking this custom hook because somehow rendering alert notifications in there is making Enzyme shit itself
// because Enzyme doesn't support React functional components

export default function useFeedbackMap() {
  return { feedbackValue: 0, update: async () => {} };
}
