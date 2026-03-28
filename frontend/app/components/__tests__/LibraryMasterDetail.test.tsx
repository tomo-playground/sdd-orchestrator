import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import LibraryMasterDetail from "../layout/LibraryMasterDetail";

// ── Helpers ──────────────────────────────────────────────────

type Item = { id: number; name: string; description?: string };

const ITEMS: Item[] = [
  { id: 1, name: "Alpha", description: "First" },
  { id: 2, name: "Beta", description: "Second" },
  { id: 3, name: "Gamma", description: "Third" },
];

const defaultProps = () => ({
  items: ITEMS,
  selectedId: null as number | null,
  onSelect: vi.fn(),
  renderDetail: (item: Item) => <div data-testid="detail">{item.name} Detail</div>,
});

// ── Tests ────────────────────────────────────────────────────

describe("LibraryMasterDetail", () => {
  let onSelect: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSelect = vi.fn();
  });

  // 1. Renders all items in the master list
  it("renders all items in the master list", () => {
    render(<LibraryMasterDetail {...defaultProps()} onSelect={onSelect} />);

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  // 2. Calls onSelect when an item is clicked
  it("calls onSelect when an item is clicked", () => {
    render(<LibraryMasterDetail {...defaultProps()} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("Beta"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  // 3. Renders detail panel when an item is selected
  it("renders detail panel for the selected item", () => {
    render(<LibraryMasterDetail {...defaultProps()} selectedId={1} onSelect={onSelect} />);

    expect(screen.getByTestId("detail")).toHaveTextContent("Alpha Detail");
  });

  // 4. Filters items by search query
  it("filters items by search input", () => {
    render(<LibraryMasterDetail {...defaultProps()} onSelect={onSelect} />);

    const input = screen.getByLabelText("Search items");
    fireEvent.change(input, { target: { value: "gam" } });

    expect(screen.getByText("Gamma")).toBeInTheDocument();
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
  });

  // 5. Shows loading skeleton
  it("shows loading skeleton when loading is true", () => {
    render(<LibraryMasterDetail {...defaultProps()} loading onSelect={onSelect} />);

    // Skeleton renders animated pulse divs, items should not appear
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    const listbox = screen.getByRole("listbox");
    expect(listbox.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  // 6. Shows empty state when no items
  it("shows empty state when items list is empty", () => {
    render(
      <LibraryMasterDetail
        {...defaultProps()}
        items={[]}
        emptyState={<span>Nothing here</span>}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  // 7. Shows "No results" when search matches nothing
  it("shows 'No results' when search yields no matches", () => {
    render(<LibraryMasterDetail {...defaultProps()} onSelect={onSelect} />);

    const input = screen.getByLabelText("Search items");
    fireEvent.change(input, { target: { value: "zzz" } });

    expect(screen.getByText("No results")).toBeInTheDocument();
  });

  // 8. Add button renders and fires onAdd
  it("renders add button and fires onAdd callback", () => {
    const onAdd = vi.fn();
    render(<LibraryMasterDetail {...defaultProps()} onAdd={onAdd} onSelect={onSelect} />);

    const addBtn = screen.getByLabelText("Add item");
    fireEvent.click(addBtn);
    expect(onAdd).toHaveBeenCalledOnce();
  });

  // 9. Add button is hidden when onAdd is not provided
  it("hides add button when onAdd is not provided", () => {
    render(<LibraryMasterDetail {...defaultProps()} onSelect={onSelect} />);

    expect(screen.queryByLabelText("Add item")).not.toBeInTheDocument();
  });

  // 10. Shows detail empty state when nothing is selected
  it("shows detail empty state when selectedId is null", () => {
    render(
      <LibraryMasterDetail
        {...defaultProps()}
        detailEmptyState={<span>Select something</span>}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText("Select something")).toBeInTheDocument();
  });

  // 11. Custom filterFn overrides default name-only filter
  it("uses custom filterFn when provided", () => {
    const customFilter = (item: Item, q: string) =>
      item.name.toLowerCase().includes(q) || (item.description?.toLowerCase().includes(q) ?? false);

    render(<LibraryMasterDetail {...defaultProps()} filterFn={customFilter} onSelect={onSelect} />);

    const input = screen.getByLabelText("Search items");
    fireEvent.change(input, { target: { value: "first" } });

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("Gamma")).not.toBeInTheDocument();
  });
});
