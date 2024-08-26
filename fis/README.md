## Fuzzy Inference System configuration files 
As of August 2024, we have one version of a FIS: version 0.1. For the file name, we replace dots with "p". The following table shows the version, release date, configuation filename, and brief notes.

| Version | Release Date | Configuration Filename | Notes |
|---------|--------------|------------------------|-------|
| 0.1     | 2024-08-01   | v0p1.py                | Initial version |

You can find a preprint on version 0.1 at this [link](https://doi.org/10.20944/preprints202408.0185.v1).

### Future 
* Aiming to release first operational version (1.0) by Dec 1 2024 for supporting the Ozone Alert system at the Bingham Research Center.
* Create DOIs for operational version to cite the codebase in publications.

## Structure of configuration files 
The configuration files are divided into sections that define the fuzzy inference system. The sections are as follows:

#### Universe of Discourse
Setting the universe of discourse for each input and output variable.

#### Membership Functions
This section defines the membership functions (MFs) for each input and output variable. MFs define how much a category for a fuzzy variable belongs to a given category, such as "sufficient snow". For example, for a snowfall of 25 mm (1 inch), which is unlikely to create a Uinta Basin cold pool, we may see this is 0.2 sufficient. Totally sufficient snow depth would be 1.0 sufficient. We define most of our MFs using convenience scikit-fuzz methods to generate shapes, such as Gaussian, triangular, and sigmoid. We can do custom MFs if desired.

#### Rules
This section defines the rules for the fuzzy inference system. Rules are craeted with `skfuzz.control.Rule` objects. Each rule has an antecedent and a consequent. The antecedent is a set of conditions that must be met for the rule to be applied. The consequent is the action taken if the rule is applied. The rules are combined using the `skfuzz.control.ControlSystem` object, which we wrap in our custom `FIS` class located in `fis.fis`.

#### Create FIS
We create both a `ControlSystem` (`*_ctrl`) and a `FIS` object (`*_sim`). The `FIS` object is a wrapper around the `ControlSystem` object that allows us to easily run the FIS and get the output.

#### How to import the control sysstem and a FIS instance base thereon
As shown in the `main.py` code, we do the following for predicting ozone concentrations using version 0.1:

```python
import importlib
version = '0.1'
v_str = version.replace('.', 'p')
version_fpath = f'fis.v{v_str}'

module = importlib.import_module(version_fpath)
```

We then import that version's control system and FIS object (and here the ozone fuzzy variable so we can access the universe of discourse for a certain method in `FIS`) as follows:

```python
ozone_ctrl = module.ozone_ctrl
ozone_sim = module.ozone_sim
ozone = module.ozone
```

This is a way to create a prediction with that FIS version using a single set of input. The two predictions we create are:

1. A crisp prediction using the `generate_crisp_inference` method.
2. A possibility distribution using the `create_possibility_array` method.

```python
inputs = {
    'snow': 100,
    'mslp': 1040E2,
    'wind': 1.5,
    'solar': 500
}

print(ozone_sim.generate_crisp_inference(inputs))
print(ozone_sim.create_possibility_array())
```

Code for obtaining NWP data as inputs is found elsewhere in the `clyfar` package, such as `clyfar.nwp`.
