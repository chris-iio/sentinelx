import { init } from "./clipboard";

describe("clipboard copy buttons", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("uses one delegated click handler for existing and later copy buttons", async () => {
    document.body.innerHTML = `
      <button class="copy-btn" data-value="1.2.3.4" type="button">
        <span>Copy</span>
      </button>
    `;
    const addEventListenerSpy = vi.spyOn(document, "addEventListener");
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    init();
    init();

    document.querySelector<HTMLElement>(".copy-btn span")?.click();

    const dynamicButton = document.createElement("button");
    dynamicButton.className = "copy-btn";
    dynamicButton.type = "button";
    dynamicButton.setAttribute("data-value", "evil.example");
    dynamicButton.setAttribute("data-enrichment", "malicious");
    dynamicButton.textContent = "Copy";
    document.body.appendChild(dynamicButton);
    dynamicButton.click();

    await Promise.resolve();

    expect(addEventListenerSpy.mock.calls.filter(([eventName]) => eventName === "click")).toHaveLength(1);
    expect(writeText).toHaveBeenCalledTimes(2);
    expect(writeText).toHaveBeenNthCalledWith(1, "1.2.3.4");
    expect(writeText).toHaveBeenNthCalledWith(2, "evil.example | malicious");
  });
});
