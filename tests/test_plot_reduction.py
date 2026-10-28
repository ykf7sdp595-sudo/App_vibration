import unittest
import numpy as np
import pandas as pd
from plotting import reduce_plot_points

class ReductionTests(unittest.TestCase):
    def test_limit_and_narrow_extrema(self):
        y=np.zeros(19999); y[123]=100; y[17892]=-90
        df=pd.DataFrame({'y':y,'z':-y})
        result=reduce_plot_points(df,['y','z'],1000)
        self.assertLessEqual(len(result),1000)
        self.assertTrue({0,123,17892,19998}.issubset(result.index))
        self.assertEqual(len(df),19999)

    def test_gaps_preserved(self):
        df=pd.DataFrame({'y':np.arange(100,dtype=float)})
        df.loc[42,'y']=np.nan
        self.assertIn(42,reduce_plot_points(df,['y'],20).index)

    def test_small_input_unchanged(self):
        df=pd.DataFrame({'y':[1.,2.]})
        self.assertIs(reduce_plot_points(df,['y'],10),df)
