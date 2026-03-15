import random
import time
import csv
import os
import matplotlib.pyplot as plt

DEFAULT_POPULATION_SIZE = 100
DEFAULT_MUTATION_RATE = 0.01
DEFAULT_CROSSOVER_RATE = 0.7
MAX_GENERATIONS = 1000

BIT_LENGTH = 32

# Parameter ranges for tuning 
POPULATION_SIZES = [50, 100, 200]
MUTATION_RATES = [0.01, 0.05, 0.1]
CROSSOVER_RATES = [0.6, 0.7, 0.9]

TRIALS_PER_SETTING = 10

OUTPUT_DIR = "ga_outputs"
RUNS_DIR = os.path.join(OUTPUT_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)


def generate_passcode(length=BIT_LENGTH) -> str:
    return ''.join(random.choice('01') for _ in range(length))


def generate_individual(length=BIT_LENGTH) -> str:
    return ''.join(random.choice('01') for _ in range(length))


def calculate_fitness(individual: str, target: str) -> int:
    return sum(1 for a, b in zip(individual, target) if a == b)


def mutate(individual: str, mutation_rate: float) -> str:
    return ''.join(
        bit if random.random() > mutation_rate else ('1' if bit == '0' else '0')
        for bit in individual
    )


def crossover(parent1: str, parent2: str, crossover_rate: float):
    if random.random() < crossover_rate:
        point = random.randint(1, BIT_LENGTH - 1)  
        c1 = parent1[:point] + parent2[point:]
        c2 = parent2[:point] + parent1[point:]
        return c1, c2
    return parent1, parent2


def evolve_population(population, target, mutation_rate, crossover_rate):
    ranked = sorted(population, key=lambda ind: calculate_fitness(ind, target), reverse=True)

    new_pop = [ranked[0]]

    top_half = ranked[:len(ranked) // 2]

    while len(new_pop) < len(population):
        p1 = random.choice(top_half)
        p2 = random.choice(top_half)

        c1, c2 = crossover(p1, p2, crossover_rate)
        new_pop.append(mutate(c1, mutation_rate))

        if len(new_pop) < len(population):
            new_pop.append(mutate(c2, mutation_rate))

    return new_pop


def genetic_algorithm(target, pop_size, mutation_rate, crossover_rate,
                      max_generations=MAX_GENERATIONS, verbose=False):
   
    population = [generate_individual() for _ in range(pop_size)]
    start_time = time.time()

    best_fitness_history = []

    for gen in range(max_generations + 1):
        best_individual = max(population, key=lambda ind: calculate_fitness(ind, target))
        best_fitness = calculate_fitness(best_individual, target)
        best_fitness_history.append(best_fitness)

        if verbose:
            print(f"Generation {gen}: Best fitness = {best_fitness}/{len(target)}")

        if best_fitness == len(target):
            end_time = time.time()
            return True, best_individual, gen, (end_time - start_time), best_fitness_history

        population = evolve_population(population, target, mutation_rate, crossover_rate)

    end_time = time.time()
    return False, best_individual, max_generations, (end_time - start_time), best_fitness_history


def save_convergence_curve(filepath, history):
    with open(filepath, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["generation", "best_fitness"])
        for i, fit in enumerate(history):
            w.writerow([i, fit])


def parameter_tuning():
    passcodes = [generate_passcode() for _ in range(TRIALS_PER_SETTING)]

    summary_path = os.path.join(OUTPUT_DIR, "tuning_summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "population_size", "mutation_rate", "crossover_rate",
            "trial", "passcode", "success", "generations", "time_sec"
        ])

        
        agg = {} 

        for pop_size in POPULATION_SIZES:
            for mut_rate in MUTATION_RATES:
                for cross_rate in CROSSOVER_RATES:
                    key = (pop_size, mut_rate, cross_rate)
                    agg[key] = []

                    print(f"\nTesting setting: Pop={pop_size}, Mut={mut_rate}, Cross={cross_rate}")

                    for trial_idx, pc in enumerate(passcodes, start=1):
                        success, best, gens, tsec, history = genetic_algorithm(
                            target=pc,
                            pop_size=pop_size,
                            mutation_rate=mut_rate,
                            crossover_rate=cross_rate,
                            max_generations=MAX_GENERATIONS,
                            verbose=False
                        )

                        run_curve_path = os.path.join(
                            RUNS_DIR,
                            f"convergence_pop{pop_size}_mut{mut_rate}_cross{cross_rate}_trial{trial_idx}.csv"
                        )
                        save_convergence_curve(run_curve_path, history)

                        w.writerow([pop_size, mut_rate, cross_rate, trial_idx, pc, int(success), gens, f"{tsec:.4f}"])
                        agg[key].append((gens, tsec, success, history))

    print(f"\nSaved summary to: {summary_path}")
    print(f"Saved convergence curves to: {RUNS_DIR}")

    plot_outputs(agg)


def plot_outputs(agg):
    # 1) Plot average generations for each setting (simple "tuning effect")
    avg_gen_path = os.path.join(OUTPUT_DIR, "avg_generations.png")
    labels = []
    avg_gens = []

    for (pop, mut, cross), runs in agg.items():
        gens_list = [r[0] for r in runs]
        avg = sum(gens_list) / len(gens_list)
        labels.append(f"P{pop}-M{mut}-C{cross}")
        avg_gens.append(avg)

    plt.figure(figsize=(14, 6))
    plt.plot(labels, avg_gens, marker="o")
    plt.xticks(rotation=75, ha="right")
    plt.ylabel("Average generations to solve (over trials)")
    plt.title("Parameter Tuning Effect (Average Generations)")
    plt.tight_layout()
    plt.savefig(avg_gen_path, dpi=200)
    plt.close()
    print(f"Saved plot: {avg_gen_path}")


    # 2) Convergence curve for EACH setting (27 plots)
    convergence_27 = os.path.join(OUTPUT_DIR, "convergence_27")
    os.makedirs(convergence_27, exist_ok=True)

    for (pop, mut, cross), runs in agg.items():
        histories = [r[3] for r in runs] 
        max_len = max(len(h) for h in histories)

        padded = []
        for h in histories:
            if len(h) < max_len:
                h = h + [h[-1]] * (max_len - len(h))
            padded.append(h)

        avg_curve = [
            sum(padded[t][g] for t in range(len(padded))) / len(padded)
            for g in range(max_len)
        ]

        plt.figure(figsize=(9, 5))
        plt.plot(range(max_len), avg_curve)
        plt.xlabel("Generation")
        plt.ylabel("Average best fitness")
        plt.title(f"Convergence Rate - Pop={pop}, Mut={mut}, Cross={cross}")
        plt.tight_layout()

        out_path = os.path.join(convergence_27, f"conv_P{pop}_M{mut}_C{cross}.png")
        plt.savefig(out_path, dpi=200)
        plt.close()

    print(f"Saved 27 convergence plots to: {convergence_27}")

    # 3) Plot convergence curves for the TOP 3 settings (fastest avg generations)
    sorted_settings = sorted(
        agg.items(),
        key=lambda kv: sum(r[0] for r in kv[1]) / len(kv[1])
    )[:3]

    conv_path = os.path.join(OUTPUT_DIR, "convergence_curves_top3.png")
    plt.figure(figsize=(10, 6))

    for (pop, mut, cross), runs in sorted_settings:
        histories = [r[3] for r in runs]
        max_len = max(len(h) for h in histories)
        padded = []
        for h in histories:
            if len(h) < max_len:
                h = h + [h[-1]] * (max_len - len(h))
            padded.append(h)

        avg_curve = [sum(padded[t][g] for t in range(len(padded))) / len(padded) for g in range(max_len)]
        plt.plot(range(max_len), avg_curve, label=f"Pop={pop}, Mut={mut}, Cross={cross}")

    plt.xlabel("Generation")
    plt.ylabel("Average best fitness")
    plt.title("Convergence Rate (Average Fitness Curve) - Top 3 Settings")
    plt.legend()
    plt.tight_layout()
    plt.savefig(conv_path, dpi=200)
    plt.close()
    print(f"Saved plot: {conv_path}")


if __name__ == "__main__":
    #seed(123) # For reproducibility during testing

    demo_passcode = generate_passcode()
    print("Demo Passcode:", demo_passcode)

    success, best, gens, tsec, history = genetic_algorithm(
        target=demo_passcode,
        pop_size=DEFAULT_POPULATION_SIZE,
        mutation_rate=DEFAULT_MUTATION_RATE,
        crossover_rate=DEFAULT_CROSSOVER_RATE,
        verbose=True
    )

    print("\n--- Demo Result ---")
    print("Success:", success)
    print("Best:", best)
    print("Generations:", gens)
    print(f"Time taken: {tsec:.4f} seconds")

    demo_curve_path = os.path.join(OUTPUT_DIR, "demo_convergence.csv")
    save_convergence_curve(demo_curve_path, history)

    parameter_tuning()
