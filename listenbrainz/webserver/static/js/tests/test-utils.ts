// eslint-disable-next-line import/no-extraneous-dependencies
import { ReactWrapper } from "enzyme";
import { act } from "react-dom/test-utils";

// eslint-disable-next-line import/prefer-default-export
export async function waitForComponentToPaint<P = {}>(
  wrapper: ReactWrapper<P>,
  amount = 0
) {
  await act(async () => {
    await new Promise((resolve) => {
      setTimeout(resolve, amount);
    });
    wrapper.update();
  });
}
